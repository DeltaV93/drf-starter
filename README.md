# DRF Starter

A Django REST Framework + React starter you can clone and have running in one
command, with the auth, billing, tooling and CI already wired up.

- **Backend** — Django 5.2 LTS, DRF, PostgreSQL, Celery + Redis, drf-spectacular
- **Frontend** — React 19, TypeScript, Vite, MUI, jotai, react-hook-form, i18next
- **Auth** — session cookies with CSRF, registration, email verification,
  password reset, GDPR-compliant account deletion
- **Billing** — Stripe hosted Checkout, optional and removable
- **Teams** — organizations, per-org roles, invitations and seat limits, optional
- **API keys** — hashed, scoped, expiring credentials for machine access, optional
- **Audit log** — append-only, allow-listed metadata, retention command, optional
- **Two-factor** — TOTP with hashed single-use recovery codes, optional
- **Uploads** — content-sniffed, size-limited, private-by-default S3 storage, optional
- **Theming** — the whole look from one token file, light and dark
- **Tooling** — ruff, ESLint, pytest, Vitest, pre-commit with secret scanning,
  GitHub Actions, Docker

## Documentation

| | |
|---|---|
| [Configuration](docs/configuration.md) | Every environment variable, its default, and what it does. Kept in step with the code by a test |
| [Architecture](docs/architecture.md) | What is here, how a request moves through it, and why the flags are independent |
| [Extending](docs/extending.md) | Recipes: a new endpoint, a new feature behind a flag, a page, a task, a locale |
| [Theming](#theming) | Re-skinning the SPA for a new brand |
| [CLAUDE.md](CLAUDE.md) | The decisions that are easy to undo by accident. Read before changing anything structural |

The rest of this file is the tour: quick start, then a section per feature
including how to delete it.

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
  organizations/   teams, membership, invitations (optional)
  api_keys/        programmatic access credentials (optional)
  audit/           append-only record of security-relevant actions (optional)
  uploads/         validated file storage, S3-backed (optional)
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

### Feature flags come in pairs

Every optional feature is gated twice: once on the backend, where the flag
decides `INSTALLED_APPS`, URLs and middleware, and once at the SPA's build
time, where the matching `VITE_` variable decides whether the UI is rendered
at all.

| Backend | Frontend |
|---|---|
| `STRIPE_ENABLED` | `VITE_STRIPE_ENABLED` |
| `SOCIAL_AUTH_ENABLED` | `VITE_SOCIAL_AUTH_ENABLED` |
| `ORGANIZATIONS_ENABLED` | `VITE_ORGANIZATIONS_ENABLED` |
| `API_KEYS_ENABLED` | `VITE_API_KEYS_ENABLED` |
| `AUDIT_LOG_ENABLED` | `VITE_AUDIT_LOG_ENABLED` |
| `TWO_FACTOR_ENABLED` | `VITE_TWO_FACTOR_ENABLED` |
| `UPLOADS_ENABLED` | `VITE_UPLOADS_ENABLED` |

They have to agree. Frontend on and backend off renders a page whose every
call 404s; the reverse leaves a working API with no way to reach it. Vite
inlines these at build time, so in Docker they are `--build-arg`s, not runtime
environment variables — changing one on a deployed container does nothing until
the image is rebuilt.

The one exception is the data export, which has no flag: portability is the
other half of the erasure the template already implements, so it is always on.

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

Billing endpoints live under `/api/v1/billing/` when `STRIPE_ENABLED` is true,
and organization endpoints under `/api/v1/organizations/` when
`ORGANIZATIONS_ENABLED` is.

Interactive docs: `/api/docs/` (Swagger), `/api/redoc/`, `/api/schema/`.

### Email verification

Registration signs the user in immediately and sends a verification email.
Nothing is gated on verification by default — add
`apps.authentication.permissions.IsEmailVerified` to the views that should
require it.

### Data export

`POST /api/v1/account/export/` assembles the user's data and emails them a
link; `GET /api/v1/account/export/<token>/` serves it as a JSON download. No
feature flag — portability is the other half of the erasure below, and a
template should not ship half a regulation.

**The link goes to the account's own address**, not back in the response, so
holding a session is not the same as receiving the data. It is a signed,
time-limited token rather than a stored row: nothing to clean up, and an aged
link stops working without anyone expiring it. The salt namespaces it, so a
signature minted elsewhere in the project is not accepted here.

**Credentials are stripped at any depth** — `password`, `hashed_secret`,
`token_hash` and friends — on top of each collector choosing its own fields.
That is deliberate belt and braces: a collector that later grows a field cannot
leak one by accident. An export is a file the user may forward, store or lose.

**Sections come from registered collectors**, wired up in `apps.core`'s
`ready()` according to which flags are on, so an optional app contributes its
data only when it is installed and this module imports nothing that might not
be there. Add your own with `register_collector(name, callable)`.

A collector that raises does not lose the rest of the export — a partial export
the user can act on beats a 500 they cannot.

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
way -- see **Social login** below.

---

## Organizations (teams)

Off by default. `ORGANIZATIONS_ENABLED=true` plus `VITE_ORGANIZATIONS_ENABLED=true`
on the frontend turns on the B2B shape: users belong to organizations, with
per-organization roles, invitations and seat limits.

**Roles are per organization**, and deliberately separate from
`CustomUser.role`, which is product-wide. The same person can own one
organization and be a plain member of another.

| Role | Can |
|---|---|
| `OWNER` | everything, including transferring ownership |
| `ADMIN` | invite, remove, change roles, rename |
| `MEMBER` | read the member list |

**The active organization lives in the session**, not in a header or the
request body — a caller cannot name an organization they do not belong to, and
views do not each have to re-check. `apps/organizations/context.py` resolves it,
falling back to the user's only membership so nobody with one organization has
to choose it.

**The last owner cannot leave, be removed, or be demoted.** An organization
with no owner cannot be administered, billed or cancelled by anyone, and
recovering it needs a database shell.

**Invitations are single-use, expiring, and bound to the address they were sent
to.** The database stores only a SHA-256 digest of the token — the raw value
exists solely in the email, and no endpoint returns it, so neither a database
dump nor an admin reading an API response can redeem one. Every failure answers
identically, so probing tokens reveals nothing.

**Seats.** When billing is on, `SubscriptionPlan.user_limit` is enforced against
members *plus pending invitations* — otherwise a two-seat plan is walked past by
sending five invitations. With `STRIPE_ENABLED` off there is no limit, so the
two flags stay independent.

### Removing it

```bash
git rm -r apps/organizations website/src/components/pages/OrganizationPage.tsx
git rm website/src/components/pages/AcceptInvitationPage.tsx website/src/store/organization.ts
git rm templates/emails/organization_invitation.html
```

Then drop the `ORGANIZATIONS_ENABLED` branches from `template/settings/base.py`
and `template/urls.py`, and the routes from `website/src/App.tsx`. Nothing
outside the app holds a foreign key into it, so nothing else needs touching.

---

## API keys

Off by default; `API_KEYS_ENABLED=true` plus `VITE_API_KEYS_ENABLED=true` on
the frontend turns them on. Session cookies serve a
browser and nothing else — this is the credential for a CLI, a CI job or a
server-to-server integration.

```bash
curl -H 'Authorization: Api-Key <prefix>.<secret>' https://example.com/api/v1/users/me/
```

**The key is shown once, at creation, and is not recoverable afterwards** — by
you, by staff, or by anyone with database access. Only a SHA-256 digest of the
secret half is stored. The prefix is not secret and is stored in the clear on
purpose: it makes a key identifiable in a listing and in a log, and lets lookup
be one indexed query instead of a scan that hashes every row. A key found in a
log can therefore be revoked without anyone learning its secret.

**Keys cannot manage keys.** The management endpoints accept sessions only. If
a key could mint keys, a leaked read-only key would buy a write key, and a
stolen key would mint replacements that survive revoking the original —
revocation would stop being a containment tool.

**Scopes.** `read` allows safe methods; `write` allows the rest. Enforcement is
opt-in per view via `apps.api_keys.permissions.HasWriteScope`, which ignores
requests that did not come from a key — a browser session already carries the
user's full authority.

**Revoking, not deleting.** A revoked key keeps its row, so `last_used_at` and
the prefix stay available when working out what a leaked key reached.

Key traffic is throttled under its own `api_key` scope rather than spending the
interactive user's `THROTTLE_USER` allowance.

### Removing it

```bash
git rm -r apps/api_keys
```

Then drop the `API_KEYS_ENABLED` branches from `template/settings/base.py` and
`template/urls.py`, and the `ApiKeysSection` from
`website/src/components/pages/SecurityPage.tsx`. Nothing else references it.

---

## Audit log

Off by default; `AUDIT_LOG_ENABLED=true` plus `VITE_AUDIT_LOG_ENABLED=true` on
the frontend turns it on. Usually the first thing a
B2B security review asks for.

**Append-only.** `save()` on an existing row raises, `delete()` raises, and the
admin allows neither adding, editing nor deleting. A log an administrator can
rewrite answers none of the questions it is kept for. Retention is the one way
rows leave, and it is `manage.py prune_audit_log`, which drops whole rows by age
and cannot alter one.

**Written from explicit call sites**, not from a blanket `post_save` signal. A
signal records mostly noise, and — worse — records whatever happens to be on the
model, which is how a password hash ends up in a table nobody thought was
sensitive.

**Metadata is allow-listed per action.** Anything not on the list for that action
is dropped and logged; a set of never-stored keys (`password`, `token`,
`secret`, `card_number`, …) is refused whatever the allow-list says. An action
with no allow-list entry stores no metadata at all, so adding one without
deciding what it may carry is safe by default.

**Recording never raises.** A login that 500s because the log table is full is a
worse outcome than a missing row.

**The actor is `SET_NULL`, and `actor_label` is a copy.** Deleting a user must
not erase the record that they were deleted — often the entry that matters most.

Users read their own activity at `/api/v1/account/activity/`. There is no
endpoint returning everyone's: staff read the admin, which is access-controlled
separately rather than through a surface a stolen session could reach.

Add an action by adding it to `AuditAction` in `apps/core/audit.py` *and* to
`Action` in `apps/audit/models.py` — a test fails if the two drift. The
vocabulary lives in `core` because the call sites are in apps that are always
installed, and this one is not.

### Removing it

```bash
git rm -r apps/audit
```

Then drop the `AUDIT_LOG_ENABLED` branches from `template/settings/base.py` and
`template/urls.py`, and the `ActivitySection` from
`website/src/components/pages/SecurityPage.tsx`. The `audit()` calls scattered
through the other apps can
stay: they import from `apps/core/audit.py`, which no-ops when the flag is off.

---

## Two-factor authentication

Off by default; `TWO_FACTOR_ENABLED=true` plus `VITE_TWO_FACTOR_ENABLED=true`
on the frontend turns it on. TOTP, so any
authenticator app works. Per-user and opt-in — it does not force enrolment.

| | |
|---|---|
| `POST /api/v1/auth/2fa/enrol/` | begin; returns the provisioning URI (needs the password) |
| `POST /api/v1/auth/2fa/confirm/` | activate with a code; returns the recovery codes |
| `POST /api/v1/auth/2fa/verify/` | finish a login that stopped for the second factor |
| `POST /api/v1/auth/2fa/disable/` | turn it off (needs the password) |
| `POST /api/v1/auth/2fa/recovery-codes/` | reissue (needs the password) |

**Login becomes two steps.** With a confirmed device, `POST /auth/login/` answers
`{"twoFactorRequired": true}` and — importantly — does **not** call `login()`.
`request.user` stays anonymous, so every `IsAuthenticated` view already refuses;
the pending state lives in the session and can do exactly one thing, be
verified. It expires after `TWO_FACTOR_PENDING_TIMEOUT` seconds, because a
password-verified state should not sit in a cookie indefinitely.

**A device is inactive until confirmed.** Storing a secret without proving the
user can generate codes from it is how people lock themselves out.

**Codes cannot be replayed.** A TOTP code is valid for its whole window, so the
step of the last accepted code is recorded and anything at or below it is
refused. One consequence worth knowing: confirming enrolment consumes that
step, so signing in elsewhere within the same 30 seconds asks for the next
code. That is the correct answer — it is the same code.

**The secret is encrypted at rest** with a key derived from
`TWO_FACTOR_SECRET_KEY`, falling back to `SECRET_KEY`. A TOTP secret is a bearer
credential: whoever holds it can generate valid codes forever, so a database
dump alone should not be enough.

> **Before rotating `SECRET_KEY`:** set `TWO_FACTOR_SECRET_KEY` first. Otherwise
> rotation makes every enrolled secret undecryptable and locks those users out
> of their own accounts — worse than the session invalidation rotation already
> causes. Decryption failure fails *closed*, so it can never be mistaken for a
> valid code.

**Recovery codes are hashed and single use**, ten of them, shown once. Reissuing
invalidates the previous set; disabling deletes them, so a stale one cannot work
against a later enrolment.

**Enrolling, disabling and reissuing all require the current password.** A
session left open on a shared machine should not be enough to add a factor the
real owner cannot produce, or to remove the one protecting them.

### Removing it

Delete `apps/authentication/two_factor.py`, `two_factor_services.py`,
`views_two_factor.py`, `serializers_two_factor.py` and the two models in
`apps/authentication/models.py` (with a migration), drop `pyotp` from
`requirements/base.txt`, and remove the `TWO_FACTOR_ENABLED` branches from
`template/settings/base.py`, `apps/authentication/urls.py` and `LoginView`.
On the frontend, drop the `TwoFactorSection` from
`website/src/components/pages/SecurityPage.tsx` and the code step from
`LoginPage.tsx` and `store/auth.ts`.

---

## File uploads

Off by default; `UPLOADS_ENABLED=true` plus `VITE_UPLOADS_ENABLED=true` on the
frontend turns them on.

> **The local filesystem backend is a development convenience only.** Container
> filesystems are ephemeral — on Railway, Render, Fly or any rebuild, every
> uploaded file is gone, silently, leaving rows pointing at nothing. Set
> `AWS_STORAGE_BUCKET_NAME` before you accept a single real upload.

**The type comes from the file's own bytes**, never from the `Content-Type`
header or the extension — both are supplied by the uploader. A shell script
called `avatar.png` announced as `image/png` is a shell script, and is refused.
Unrecognised formats are refused too: `UPLOAD_ALLOWED_TYPES` is an allow-list,
not a deny-list.

**The uploaded filename is never used to build a path** — not even sanitised. It
can carry `../`, a null byte, a second extension, a name long enough to break a
filesystem, or a right-to-left override that makes `exe` render as `gpj`. Stored
names are generated, with the extension derived from the *sniffed* type. The
original is kept in a column for display.

**Private by default**, with the bucket ACL unset and query-string auth on. A
public bucket turns every key into a permanent public URL the moment one leaks.
Downloads go through `/api/v1/files/<id>/download/`, which checks who is asking
and then redirects to a URL that expires after
`UPLOAD_URL_EXPIRY_SECONDS` — so the application never becomes the bandwidth
path. Ownership is checked rather than trusted to an unguessable path, because a
leaked URL stays valid and a permission check does not.

**Deleting removes the bytes as well as the row.** An orphaned object in a bucket
is invisible and paid for indefinitely.

Files are partitioned by purpose and user id, so no single directory accumulates
everything.

### Removing it

```bash
git rm -r apps/uploads
```

Then drop `django-storages` from `requirements/base.txt`, the
`UPLOADS_ENABLED` branches from `template/settings/base.py` and
`template/urls.py`, and
`website/src/components/pages/FilesPage.tsx` with its route in `App.tsx`.

---

## Social login

Off by default; `SOCIAL_AUTH_ENABLED=true` plus a provider's key, and
`VITE_SOCIAL_AUTH_ENABLED=true` on the frontend. Providers are offered only when
their key is configured, so a button never appears for one that would fail on
the redirect.

**A social identity is never given an existing account by matching email.**
python-social-auth's default pipeline includes `associate_by_email`, which does
exactly that — and it is an account-takeover path: anyone who can make a
provider assert an address inherits the password account. That covers providers
that do not verify email at all, unverified accounts on ones that usually do,
and compromised ones.

This template replaces that step. An unrecognised identity whose email already
belongs to someone is refused, and the user is told to sign in with their
password and link the provider deliberately. The guard runs *before*
`create_user` — after it, the account would already exist. Putting
`associate_by_email` back turns six tests red.

**An address is marked verified only when the provider says it verified it.**
Google reports `email_verified`; several providers report nothing. Absent a
positive signal the address stays unverified and the normal confirmation email
applies — which is what stops a provider that does not verify from minting
pre-verified accounts.

**Unlinking is refused when it would leave no way to sign in.** Without a usable
password, the last provider is the only credential, and password reset cannot
help because there is nothing to reset to.

Only `username`, `email`, `first_name` and `last_name` are stored. Providers
return far more, and keeping it is a data-protection liability nobody asked for.

---

## Theming

Everything visual comes from **`website/src/styles/brand.ts`**. No component
hardcodes a colour or a radius, so a re-brand is one file:

```ts
export const identity = {
  name: 'Thornbury',
  tagline: 'Field notes for growers',
};

export const lightPalette: BrandPalette = {
  primary: { main: '#1b5e3f', light: '#3d8563', dark: '#0e3d28', contrastText: '#fff' },
  // ...
};
```

That name reaches the browser tab, the header and the footer; the palette
reaches every button, link, chip and surface. `styles/theme.ts` turns the
tokens into the MUI theme and contains no literals of its own -- you should
not need to open it.

**Change both palettes.** `lightPalette` and `darkPalette` are separate
objects, and the commonest re-branding mistake is editing the first, seeing
the new colours, and shipping a dark mode still wearing the template's. The
suite checks that the two agree on hue and says so by name when they do not.

**Colours are checked for contrast.** `styles/theme.test.ts` computes the WCAG
ratio for every `contrastText` against its own `main`, and for body text
against both surfaces. A palette that looks fine to whoever picked it and is
unreadable in daylight fails the build with the ratio in the message.

Three of Material's own defaults -- `warning` and `info` in light, `error` in
dark -- sit between 3:1 and 4.5:1. They clear the bar for a chip or an icon
but not for a paragraph of body text. They are listed explicitly in
`BELOW_AA_TEXT` rather than tolerated silently, so anything you introduce is
held to the full 4.5:1. Darkening those three empties the list.

### Light and dark

MUI's `colorSchemes` keeps both palettes in one stylesheet, switched by a
`data-mui-color-scheme` attribute on `<html>`. The header's control offers
light, dark and *system* -- three states, because a plain two-way switch has
no way back to following the OS once it has been touched.

An inline script in `index.html` applies the saved scheme **before the bundle
loads**. Without it a returning dark-mode visitor gets a white flash while
React starts up. The script and `colorSchemeSelector` in `theme.ts` have to
name the same attribute; a test reads the HTML and checks they do, because
nothing else would notice -- the app still works, it just blinks.

### What is not in brand.ts

Two things cannot read a token, and both are called out where they live:

- **`public/favicon.svg`** -- the browser fetches it before any JavaScript
  runs, so the brand colour is repeated in the file.
- **`index.html`** -- static, so the title, description and the two
  `theme-color` values are substituted at build time by the `brandHtml()`
  plugin in `vite.config.ts`, which imports `brand.ts`.

### Fonts

The default stack is the system UI font, so there is no webfont request
blocking the first paint and no third party seeing every page view. To use a
brand face, add its `@font-face` or a `<link>` in `index.html` and put the
family first in `fontFamily` -- keeping the rest as fallbacks so text still
renders while the file downloads.

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

The catch-all deliberately refuses anything with a file extension, and any
path under `api/`, `admin`, `assets/`, `static/` or `media/`. A client-side
route has no extension, so a request for `/assets/index-abc123.js` that
WhiteNoise did not serve is a *missing file* and gets a 404. Answering it with
`index.html` instead -- which an earlier version did -- hands the browser HTML
where it asked for JavaScript: the script is silently rejected, the page
renders blank, and the server log shows a wall of 200s. If you add a
client-side route containing a dot, widen `SPA_FILE_LIKE_PATH`.

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

### Error tracking

Set `SENTRY_DSN` and error reporting turns itself on; leave it unset and
nothing is imported. There is no separate flag.

`send_default_pii` is **off** by default, so email addresses, usernames and IP
addresses are not sent to a third party unless you set `SENTRY_SEND_PII=true`
deliberately. Performance sampling is off too (`SENTRY_TRACES_SAMPLE_RATE`),
because it costs quota. Railway and Render expose the deployed commit, which is
picked up automatically so a traceback points at a revision rather than just at
"production"; `SENTRY_RELEASE` overrides it.

It is never armed during a test run, so a DSN sitting in a CI environment
cannot fill a real project with noise from tests that fail on purpose.

### Sending email in the background

Verification and password-reset mail is sent inside the request by default,
which means a slow SMTP round trip shows up directly in response times. Set
`EMAIL_ASYNC=true` and delivery moves onto Celery instead — you need a worker:

```bash
celery -A template worker --loglevel=info
```

Templates are still rendered in the request either way. Only delivery moves, so
a broken template fails the request that caused it rather than disappearing
into a worker log, and nothing but strings crosses the queue.

It is off by default because the default compose stack runs no worker, and a
queued message nobody drains is worse than a slow one.

Set `DJANGO_SUPERUSER_USERNAME`, `_EMAIL` and `_PASSWORD` to have the
entrypoint create an admin on first boot. It is a no-op unless all three
are set.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
