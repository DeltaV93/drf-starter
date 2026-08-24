# Architecture

What is here, how a request moves through it, and why the pieces are arranged
the way they are. Read this before changing anything structural; read
[extending.md](extending.md) when you want to add something.

## The shape

A Django REST Framework API and a React single-page app, served from one
container. The SPA talks to the API over session cookies on the same origin,
so there is no token to store and no CORS preflight in the common case.

```
                    ┌─────────────────────────────────────────┐
   browser ────────▶│ gunicorn                                │
                    │  ├── WhiteNoise ──▶ /assets/*, /static/*│
                    │  └── Django                             │
                    │       ├── /api/v1/*  ──▶ DRF views      │
                    │       ├── /admin/    ──▶ Django admin   │
                    │       └── everything else ──▶ index.html│
                    └──────────┬──────────────────────────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
              Postgres      Redis       Celery worker
                          (cache +      (email, exports,
                           broker)       reports)
```

The worker is optional. With `EMAIL_ASYNC=false` — the default — mail is sent
in the request and nothing needs draining.

## Layout

| Directory | What lives there |
|---|---|
| `apps/core` | Health probes, throttle classes, the audit vocabulary, shared middleware |
| `apps/users` | `CustomUser` — the `AUTH_USER_MODEL` |
| `apps/authentication` | Registration, login, password reset, email verification, two-factor |
| `apps/subscriptions` | Billing. Optional |
| `apps/organizations` | Teams, memberships, invitations. Optional |
| `apps/api_keys` | Machine credentials. Optional |
| `apps/audit` | The append-only event log. Optional |
| `apps/uploads` | Attachments and avatars. Optional |
| `template/` | The project package: settings, URLs, WSGI/ASGI, Celery. Renamed by `scripts/rename_project.py` |
| `utils/` | Helpers not tied to one app: the response envelope, email, logging, GDPR export and erasure |
| `website/` | The React SPA |
| `docs/` | This directory |

## Models

Every model is scoped to `AUTH_USER_MODEL` and nothing else.

| App | Models |
|---|---|
| `users` | `CustomUser` |
| `authentication` | `TwoFactorDevice`, `RecoveryCode` |
| `subscriptions` | `SubscriptionPlan`, `Subscription`, `AddOn`, `UserAddOn`, `Invoice`, `Payment` |
| `organizations` | `Organization`, `Membership`, `Invitation` |
| `api_keys` | `APIKey` |
| `audit` | `AuditEvent` |
| `uploads` | `Attachment` |

### The rule that makes eight flags tractable

**No optional feature holds a foreign key into another optional feature.**

That is the single constraint the whole flag system rests on. Organizations are
a *lens* over members, not an owner: to see an organization's audit trail you
resolve its members and filter events by them. `AuditEvent` has no
`organization_id`, so the audit log neither knows nor cares whether
organizations exist.

Without this, turning off one feature would break the migrations of another and
the flags would be combinatorial rather than independent. With it, the apps can
be added in any order, removed in any order, and deleted with `git rm` plus a
settings branch.

The one place B2B genuinely needs a link is billing, and it needs no schema
change: `Subscription` stays attached to a user, and when organizations are on,
the org owner holds it while seats are counted against `Membership`. That is
what makes `SubscriptionPlan.user_limit` mean something.

CI proves it. The flag matrix runs the suite with everything off, everything on,
and each flag off on its own against the rest — ten configurations. It does not
cover all 2⁸; it covers the realistic failure, which is one feature quietly
depending on another.

## A request, end to end

### Middleware, in order

```
apps.core.middleware.HealthCheckMiddleware      ← must stay first
django.middleware.security.SecurityMiddleware
django.contrib.sessions.middleware.SessionMiddleware
corsheaders.middleware.CorsMiddleware
django.middleware.locale.LocaleMiddleware
django.middleware.common.CommonMiddleware
django.middleware.csrf.CsrfViewMiddleware       ← never comment this out
django.contrib.auth.middleware.AuthenticationMiddleware
django.contrib.messages.middleware.MessageMiddleware
django.middleware.clickjacking.XFrameOptionsMiddleware
apps.subscriptions.middleware.SubscriptionMiddleware
```

Two positions are load-bearing:

**`HealthCheckMiddleware` runs before `SecurityMiddleware`.** It has to answer
before the SSL redirect and before anything calls `request.get_host()`, or a
platform health probe gets a 301 or a 400 instead of the 200 it needs. That is
what broke the first Railway deploy. `production.py` rebuilds the list to insert
WhiteNoise and must preserve the ordering; development inserts debug-toolbar
ahead of it, which is harmless because only the position relative to
`SecurityMiddleware` matters. Pinned by `apps/core/tests/test_health_probes.py`
in every environment.

**`CsrfViewMiddleware` stays enabled.** It was commented out once. Session auth
without CSRF is not session auth. Pinned by
`apps/authentication/tests/test_csrf.py`.

### URL resolution

Routes live under `/api/v1/`, and Django URLs end in a slash. The frontend's
`routes.ts` preserves the slash, because dropping it turns every POST into an
`APPEND_SLASH` redirect that loses the body.

The SPA catch-all is **last** in `urlpatterns` and excludes `api/`, `admin/`,
`assets/`, `static/`, `media/` and anything that looks like a file. Widen it and
every endpoint starts answering with `index.html` and a 200, which nothing else
would catch — the status stays 200 the whole time it is broken; only the content
type and the size are wrong. Pinned by `apps/core/tests/test_spa.py` and by a CI
step that actually fetches every script the page references.

### Authentication

```
DEFAULT_AUTHENTICATION_CLASSES = [
    SessionAuthentication,                    ← the browser
    apps.api_keys.authentication.APIKeyAuthentication,  ← only when the flag is on
]
DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]
```

Authenticated-by-default: a new view is closed unless it says otherwise. The
API-key class is appended rather than substituted, so a browser keeps using
cookies. It is deliberately **not** a `SessionAuthentication` subclass — DRF's
session class enforces CSRF for cookie-authenticated requests, and a
key-authenticated request has no cookie to enforce against. Keeping them
separate is also what stops a key being usable as a session.

`AUTHENTICATION_BACKENDS` holds `ModelBackend` alone until
`SOCIAL_AUTH_ENABLED` adds the social ones. When there is more than one,
`login()` refuses to guess, which is why the password path passes an explicit
`backend=` — without it every registration 500s the moment social login is
turned on.

### Response shape

Every endpoint returns the `utils.api_utils.api_response` envelope:

```json
{ "status": "success", "message": "...", "data": {...}, "errors": {...} }
```

Null keys are dropped. Views are DRF `APIView` subclasses — never plain Django
`View`, which cannot render a DRF `Response`.

Endpoints that take an email address answer **identically whether or not the
account exists**, so they cannot be used to enumerate accounts. Keep it that way
when adding new ones.

## Settings

Split under `template/settings/`, selected by `DJANGO_ENVIRONMENT`:

```
base.py         everything shared; reads the environment through
                env_bool / env_list / env_int / env_float
├── development.py   console email, debug toolbar, relaxed cookies
├── production.py    HSTS, SSL redirect, WhiteNoise, platform domain
└── testing.py       SQLite, locmem cache and email, flags on
```

`template/settings/__init__.py` acts as a loader only when it *is* the settings
module — importing `template.settings.testing` directly must not drag in the
development environment as a side effect.

Three behaviours worth knowing:

- **`SECRET_KEY` fails loudly outside development.** No fallback, ever.
- **`DATABASE_URL` wins over the individual `DB_*` variables**, because that is
  what managed hosts inject.
- **`production.py` derives `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and
  `FRONTEND_URL` from the platform's domain variable**, so a first deploy boots
  before the domain is known.

Every variable is listed in [configuration.md](configuration.md), and a test
fails the build if that list drifts from the code.

## Flags

A flag gates three things, and all three have to agree:

```
STRIPE_ENABLED ──┬──▶ INSTALLED_APPS      (the app and its models)
                 ├──▶ urlpatterns         (the routes)
                 └──▶ MIDDLEWARE          (where applicable)

VITE_STRIPE_ENABLED ──▶ the components that would otherwise 404
```

The `VITE_` half is inlined at build time, so in Docker it is a `--build-arg`.
Changing it on a running container does nothing until the image is rebuilt.
`apps/core/tests/test_env_documented.py` checks that every backend flag has a
`VITE_` twin — the pairing is a convention nothing else enforces, and it is
exactly how six features once shipped backend-only.

## Background work

Celery is configured in `template/celery.py`, with Redis as both broker and
result backend.

| Module | What it runs |
|---|---|
| `utils/tasks.py` | Sending rendered email |
| `utils/gdpr_tasks.py` | Building a data export |
| `apps/subscriptions/tasks.py` | Billing housekeeping |

Templates render inline either way; only the send is deferred. In the test suite
`CELERY_TASK_ALWAYS_EAGER` is on, so tasks run synchronously and a failure
propagates instead of vanishing into a queue nobody is watching.

Management commands:

| Command | What it does |
|---|---|
| `prune_audit_log` | Deletes events past `AUDIT_LOG_RETENTION_DAYS`. Nothing expires on its own |
| `generate_monthly_report` | Billing summary |
| `create_superuser_if_not_exists` | Run by the entrypoint. A no-op unless all three `DJANGO_SUPERUSER_*` are set |

## The frontend

React 19 with MUI, jotai for state, react-hook-form, i18next, Vite.

**The server session is the source of truth.** `useAuthBootstrap` asks
`/users/me/` on load; nothing is trusted from `localStorage`. `ProtectedRoute`
waits for that answer before redirecting, so a signed-in user does not flash
past the login page on every refresh.

**`src/lib/api.ts` is the only place that touches CSRF.** Do not set
`X-CSRFToken` by hand at a call site.

**`src/lib/routes.ts` is the only place that names a backend path**, and it
preserves trailing slashes.

**`src/styles/brand.ts` is the only place that names a colour.** See
[Theming](../README.md#theming).

ESLint runs with `--max-warnings 0`, and the React Compiler rules
(`set-state-in-effect`, `incompatible-library`) catch real problems — fix the
code rather than disabling the rule.

## The API surface

Generated from the code by drf-spectacular. CI runs
`spectacular --fail-on-warn`, so a view with no declared request and response
fails the build; `make check` runs the same thing so it fails locally first.

Browse it at `/api/docs/` (Swagger) or `/api/redoc/`, with the raw schema at
`/api/schema/`.

| Prefix | Endpoints | Flag |
|---|---|---|
| `/api/v1/health/`, `/ready/` | Liveness and readiness probes | always |
| `/api/v1/auth/` | Register, login, logout, CSRF, password reset, email verification, account deletion | always |
| `/api/v1/auth/2fa/` | Status, enrol, confirm, disable, recovery codes, verify | `TWO_FACTOR_ENABLED` |
| `/api/v1/auth/social/` | Connections, connect, disconnect | `SOCIAL_AUTH_ENABLED` |
| `/api/v1/users/me/` | The signed-in user | always |
| `/api/v1/account/export/` | Request an export, download it with a signed token | always |
| `/api/v1/account/activity/` | Your own audit events | `AUDIT_LOG_ENABLED` |
| `/api/v1/billing/` | Plans, subscription, subscribe, add-ons, cancel, webhook | `STRIPE_ENABLED` |
| `/api/v1/organizations/` | List, create, switch, members, roles, invitations, leave | `ORGANIZATIONS_ENABLED` |
| `/api/v1/api-keys/` | List, create, revoke | `API_KEYS_ENABLED` |
| `/api/v1/files/` | List, upload, detail, signed download | `UPLOADS_ENABLED` |

`/api/v1/billing/webhook/` is the **only** `csrf_exempt` view in the project.
Its Stripe signature check is what authenticates it. Do not add `csrf_exempt`
anywhere else.
