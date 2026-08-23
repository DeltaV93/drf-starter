# DRF Starter

A Django REST Framework + React starter you can clone and have running in one
command, with the auth, billing, tooling and CI already wired up.

- **Backend** — Django 5.2 LTS, DRF, PostgreSQL, Celery + Redis, drf-spectacular
- **Frontend** — React 19, TypeScript, Vite, MUI, jotai, react-hook-form, i18next
- **Auth** — session cookies with CSRF, registration, email verification,
  password reset, GDPR-compliant account deletion
- **Billing** — Stripe hosted Checkout, optional and removable
- **Tooling** — ruff, ESLint, pytest, Vitest, pre-commit with secret scanning,
  GitHub Actions, Docker

---

## Quick start

### With Docker

```bash
git clone <your-repo-url> && cd <your-repo>
cp .env.example .env                 # fill in SECRET_KEY
cp website/.env.example website/.env
make up
```

The API is on http://localhost:8000, docs on http://localhost:8000/api/docs/.
Start the frontend separately with `make fe-install && make fe-dev`
(http://localhost:3000).

### Without Docker

You will need Python 3.11+, Node 20+, PostgreSQL and Redis.

```bash
make setup       # virtualenv, dependencies, .env files
make migrate
make run         # http://localhost:8000

make fe-install
make fe-dev      # http://localhost:3000
```

`make help` lists every target.

### Make it yours

The Django project package ships as `template`. Rename it before you start
building:

```bash
make rename NAME=myapp
# or: python scripts/rename_project.py myapp --display-name "My App"
```

This renames the package, rewrites every reference, and substitutes the
display name in the API docs and the UI. Run it on a clean working tree
(`--dry-run` shows what it would touch), then delete the script — a project
only gets renamed once.

---

## Layout

```
apps/
  core/            health probes, shared throttles
  users/           the user model, profile endpoints, admin
  authentication/  login, registration, password reset, verification
  subscriptions/   Stripe billing (optional)
template/
  settings/        base + development / production / testing
utils/             response envelope, email, logging, GDPR helpers
templates/emails/  transactional email templates
requirements/      base.txt, dev.txt, prod.txt
scripts/           the rename script
website/           the React SPA (see website/README.md)
```

---

## Configuration

Every value that differs between deployments comes from the environment.
`.env.example` lists all of them with comments and is generated from what the
code actually reads.

Settings are split by environment and selected with `DJANGO_ENVIRONMENT`
(`development`, `production`, `testing`); `DJANGO_SETTINGS_MODULE` stays
`template.settings`. You can also point `DJANGO_SETTINGS_MODULE` straight at
`template.settings.production`, which is what CI does.

Two things are worth knowing up front:

**`SECRET_KEY` is required outside development.** The app refuses to start
without it rather than booting with `None` and silently weakening every
signature.

**`ALLOWED_HOSTS` is required in production**, comma-separated.

---

## Authentication

The SPA authenticates with Django sessions, so unsafe requests carry a CSRF
token:

1. `GET /api/v1/auth/csrf/` sets the `csrftoken` cookie
2. `POST /api/v1/auth/login/` with `X-CSRFToken` establishes the session
3. later requests send the session cookie plus `X-CSRFToken`

The frontend handles all of this in `website/src/lib/api.ts` — no call site
deals with CSRF directly. `login()` rotates the token, so the login response
returns the fresh one.

In development the Vite dev server proxies `/api` to Django, which keeps the
SPA and the API same-origin. That is why local cookies work with plain `Lax`
and no CORS preflight. When you deploy them to different origins, set
`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and the `SameSite=None` +
`Secure=true` cookie pair.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health/` | Liveness probe |
| GET | `/api/v1/ready/` | Readiness probe (checks the database) |
| GET | `/api/v1/auth/csrf/` | Issue a CSRF cookie |
| POST | `/api/v1/auth/register/` | Create an account |
| POST | `/api/v1/auth/login/` | Sign in |
| POST | `/api/v1/auth/logout/` | Sign out |
| POST | `/api/v1/auth/password-reset/` | Request a reset email |
| GET | `/api/v1/auth/password-reset/<uid>/<token>/` | Check a reset link |
| POST | `/api/v1/auth/password-reset/confirm/` | Set a new password |
| POST | `/api/v1/auth/verify-email/` | Confirm an email address |
| POST | `/api/v1/auth/verify-email/resend/` | Resend the verification email |
| POST | `/api/v1/auth/delete-account/` | Delete (anonymize) the account |
| GET/PATCH | `/api/v1/users/me/` | Read or update the current profile |

Billing endpoints live under `/api/v1/billing/` when `STRIPE_ENABLED` is true.

Interactive docs: `/api/docs/` (Swagger), `/api/redoc/`, `/api/schema/`.

### Email verification

Registration signs the user in immediately and sends a verification email.
Nothing is gated on verification by default — add
`apps.authentication.permissions.IsEmailVerified` to the views that should
require it.

### Account deletion

Deletion anonymizes rather than dropping the row: personal fields are
overwritten, the password is made unusable, sessions are dropped, and
`date_deleted` is stamped. Related records (invoices, payments) stay
referentially intact. See `utils/gdpr_utils.py`.

### Response shape

Every endpoint answers with the same envelope, so the frontend handles
success and failure uniformly:

```json
{"status": "success", "message": "Profile retrieved.", "data": {"id": 1}}
{"status": "error", "message": "Login failed.", "errors": {"email": ["Required"]}}
```

Keys whose value is null are omitted. See `utils/api_utils.py`.

---

## Billing

Stripe is **off by default**. Turn it on with `STRIPE_ENABLED=true` plus your
keys, and `VITE_STRIPE_ENABLED=true` on the frontend. The flag gates the app
in `INSTALLED_APPS`, its URLs, and its middleware, so with it off the project
boots and passes its tests without any of it loaded — CI verifies that on
every run.

Checkout is Stripe-hosted: the backend creates a session and the frontend
navigates to its URL, so card details never reach this application. Webhooks
arrive at `/api/v1/billing/webhook/`, which is the one CSRF-exempt endpoint —
Stripe's signature is what authenticates it. Handlers are idempotent, because
Stripe retries.

Test webhooks locally with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook/
stripe trigger invoice.paid
```

### Removing billing

If you do not need it, delete rather than disable:

```bash
git rm -r apps/subscriptions
git rm website/src/components/pages/SubscriptionPage.tsx
```

Then drop `stripe` from `requirements/base.txt`, the `@stripe/*` packages from
`website/package.json`, the Stripe block from `.env.example`, and the
`STRIPE_ENABLED` branches in `template/settings/base.py` and `template/urls.py`.

Social login (`SOCIAL_AUTH_ENABLED`) works the same way and comes off the same
way.

---

## Development

| Command | What it does |
|---|---|
| `make test` | pytest + Vitest |
| `make lint` | ruff + ESLint + tsc |
| `make format` | Auto-fix both |
| `make check` | Django checks + production deploy checklist + missing migrations |
| `make schema` | Write the OpenAPI schema to `schema.yml` |
| `make migrations` | Create migrations after a model change |

Install the git hooks once with `pre-commit install`. They include ggshield
for secret scanning, which needs a `GITGUARDIAN_API_KEY` — see
[CONTRIBUTING.md](CONTRIBUTING.md), which also documents the branch
protection `main` expects.

### Tests

Backend tests default to SQLite so `pytest` runs with no services up; CI also
runs them against Postgres. The suite covers the CSRF contract, account
enumeration, token reuse, webhook idempotency, and the subscription
grace-period logic.

### Debugging

Set `DEBUGPY=1` to have `runserver` wait for a debugger on port 5678. It is
off by default — the previous version attached unconditionally, which hung
every start unless a debugger happened to be listening.

---

## Deploying

The `Dockerfile` builds a three-stage production image: the SPA is built with
Node, Python dependencies compile in their own stage, and the runtime carries
neither Node nor a compiler and runs as a non-root user. Static files are
collected at build time; migrations run in `entrypoint.sh`, which waits for
the database first.

**Django serves the SPA.** The built frontend lands in `website/dist` and
WhiteNoise serves it at the root, with a catch-all in `template/urls.py`
returning `index.html` for client-side routes. One service, one origin --
which is what makes the session cookies work without `SameSite=None` or CORS.
It switches itself on and off by whether `website/dist` exists, so local
development still uses the Vite dev server; `SERVE_SPA` overrides either way.

**Health probes bypass the host and scheme checks.** Platforms probe over
plain HTTP with their own `Host` header (Railway uses
`healthcheck.railway.app`), which would otherwise be a 301 from
`SECURE_SSL_REDIRECT` or a 400 from `ALLOWED_HOSTS` — never the 200 the probe
needs. `apps/core/middleware.py` runs first and answers `/api/v1/health/` and
`/api/v1/ready/` before either check. The responses are static, so nothing
reflects the `Host` header; every other route stays protected.

What that does not do is answer before the server is listening. `entrypoint.sh`
waits for the database and runs migrations before starting gunicorn — serving
traffic against an unmigrated schema is worse than a slow boot — so while that
wait is in progress the platform reports the health check as *service
unavailable*. That message is about the port, not about the database. The
container log carries the real reason, printed on the first failed connection
rather than only after the last.

### Railway

The repo ships a `railway.json`, so Railway builds from the `Dockerfile` and
health-checks `/api/v1/health/`.

1. **New Project → Deploy from GitHub repo →** this repository.
2. Add **Postgres** and **Redis** from the project's *+ New* menu.
3. On the web service, set variables:

   | Variable | Value |
   |---|---|
   | `DJANGO_ENVIRONMENT` | `production` |
   | `SECRET_KEY` | generate one with the command above |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` |
   | `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` to start |
   | `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | optional, creates an admin on first boot |

4. **Settings → Networking → Generate Domain.**

The `DATABASE_URL` and `REDIS_URL` values above are Railway variable
references and must be typed with the `${{...}}` braces — adding the Postgres
and Redis plugins does **not** inject their variables into the web service.
Miss `DATABASE_URL` and production refuses to start with a message saying so,
rather than quietly retrying a connection to localhost.

**Do not set `DB_HOST` and the other `DB_*` variables on a managed host.** They
are the local-development and compose path. Setting `DB_HOST` by hand is the
tempting mistake, because the host is the one part of the connection Railway
shows you — but `DB_NAME` then falls back to `app` and `DB_PASSWORD` to empty,
neither of which the provider created, and nothing else picks up the slack.
Production refuses that combination too. `DATABASE_URL` carries the host, name,
user and password together, which is why it is the only variable you need.

`PORT` and `RAILWAY_PUBLIC_DOMAIN` are injected by Railway. `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` are all derived from that domain, so
you can leave them unset — which is what lets the first deploy boot before you
know the domain.

Email defaults to SES. Until you have credentials, the console backend above
prints verification and password-reset links straight into the deploy logs,
where you can copy them out.

Other hosts work the same way: `DATABASE_URL`, `PORT` and the platform's own
domain variable are all understood, so Render and Fly need only their own
service definition.

### Deploying somewhere else

Before shipping, run the deploy checklist:

```bash
DJANGO_ENVIRONMENT=production python manage.py check --deploy
```

It should report no issues. CI runs it with `--fail-level WARNING`.

Production settings enable HSTS, SSL redirect, secure cookies, and WhiteNoise
for static files. If TLS terminates at a load balancer, leave
`USE_X_FORWARDED_PROTO=true` so Django learns the original scheme.

Logging goes to stdout — collection is the platform's job. Do not add file
handlers.

Set `DJANGO_SUPERUSER_USERNAME`, `_EMAIL` and `_PASSWORD` to have the
entrypoint create an admin on first boot. It is a no-op unless all three
are set.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
