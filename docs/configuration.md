# Configuration reference

Every environment variable this project reads, what it does, and what happens
when you leave it alone.

Nothing here is guessed. `scripts/env_vars.py` parses the source for every
environment read, and `apps/core/tests/test_env_documented.py` fails the build
if this file or either `.env.example` falls out of step with it. If you add a
setting and forget to document it, the suite says so by name.

```bash
python scripts/env_vars.py    # what is read, and what is undocumented
```

## How to read this

**Two files, read at different moments.** Backend variables go in `.env` at
the repository root (copy `.env.example`). Frontend variables go in
`website/.env` (copy `website/.env.example`) and are **inlined into the bundle
at build time** — changing one on a running container does nothing until the
image is rebuilt.

**Defaults differ by environment.** `DJANGO_ENVIRONMENT` selects a settings
module, and `development.py` and `production.py` override some of `base.py`.
Where that happens the table says so.

**Types.** `env_bool` accepts `1`, `true`, `yes`, `on` (case-insensitive);
anything else is false. `env_list` is comma-separated and strips whitespace.
`env_int` and `env_float` **refuse to start** on an unparseable value rather
than silently falling back — a typo in a timeout should not become a
production default.

---

## Core

| Variable | Default | What it does |
|---|---|---|
| `DJANGO_ENVIRONMENT` | `development` | Selects the settings module: `development`, `production` or `testing`. Everything else on this page is read after it. |
| `SECRET_KEY` | *(none)* | Signs sessions, password-reset links and CSRF tokens. **Required outside development** — the app refuses to start rather than boot with `None` and silently weaken every signature. Generate one with `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`. |
| `ALLOWED_HOSTS` | dev: `localhost,127.0.0.1,0.0.0.0,host.docker.internal,web` | Comma-separated hostnames Django will answer for. **Required in production**, where `production.py` also adds the platform's own domain. |
| `FRONTEND_URL` | `http://localhost:3000` | Where the SPA is served from. Used for CORS and CSRF defaults, and to build the links in verification and password-reset email. **Include the scheme** — a bare domain fails Django's checks with `corsheaders.E013`. |
| `LOG_LEVEL` | `INFO` | Application log level. Logging goes to stdout; there is no file handler in any settings module. |
| `DJANGO_LOG_LEVEL` | *(follows `LOG_LEVEL`)* | Django's own loggers, separately, when you want your app chatty and the framework quiet. |
| `API_TITLE` | `DRF Starter API` | Title in the generated OpenAPI schema and the docs UI. |
| `API_DESCRIPTION` | `API for DRF Starter` | Description in the same. |

## Database

`DATABASE_URL` wins over the individual `DB_*` variables whenever it is set,
because that is what managed hosts inject.

| Variable | Default | What it does |
|---|---|---|
| `DATABASE_URL` | *(none)* | A full connection URL, e.g. `postgres://user:pass@host:5432/name`. When set, every `DB_*` below is ignored. |
| `DB_NAME` | `app` | Database name. |
| `DB_USER` | `postgres` | Database user. |
| `DB_PASSWORD` | *(empty)* | Database password. |
| `DB_HOST` | `localhost` | Database host. In production there is no localhost fallback: the app refuses to start rather than retry a connection that cannot succeed. |
| `DB_PORT` | `5432` | Database port. |
| `DB_SSL_REQUIRE` | on for a remote URL, off for a local one | TLS to the database. The default is derived from the host, so docker-compose works and a managed host is encrypted, without either being configured. |
| `DB_CONN_MAX_AGE` | `60` | Seconds to keep a connection open. `0` disables persistent connections. |
| `DB_EXPOSED_PORT` | `5432` | Host port docker-compose publishes Postgres on. Change it when 5432 is already taken locally. |
| `DB_WAIT_ATTEMPTS` | `30` | How many times the container entrypoint retries the database before giving up. |
| `WAIT_FOR_DB` | `1` | Set `0` to skip the entrypoint's wait entirely. |
| `RUN_MIGRATIONS` | `1` | Set `0` to stop the entrypoint applying migrations on start — worth doing once you run them as a separate deploy step. |

## Redis, cache and Celery

| Variable | Default | What it does |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379` | Cache backend, and the base for both Celery URLs below. |
| `CELERY_BROKER_URL` | `{REDIS_URL}/0` | Override only if the broker lives apart from the cache. |
| `CELERY_RESULT_BACKEND` | `{REDIS_URL}/0` | Likewise for results. |

## Email

| Variable | Default | What it does |
|---|---|---|
| `EMAIL_BACKEND` | dev: console, otherwise `django_ses.SESBackend` | Development prints messages to the terminal, so no credentials are needed to click through a signup. |
| `DEFAULT_FROM_EMAIL` | `no-reply@example.com` | The From address on everything the app sends. |
| `AWS_ACCESS_KEY_ID` | *(none)* | Credentials for SES. Also used for S3 when uploads are on. |
| `AWS_SECRET_ACCESS_KEY` | *(none)* | |
| `AWS_SES_REGION_NAME` | `us-east-1` | SES region. Also the fallback region for S3. |
| `EMAIL_ASYNC` | `false` | Hand rendered messages to Celery instead of sending them in the request. **Needs a worker running.** Off by default because the default compose stack has none, and a queued message nobody drains is worse than a slow one. |

## Feature flags

Each of these gates `INSTALLED_APPS`, URLs and middleware, and each has a
`VITE_` twin below that gates the UI. **They have to agree**: frontend on with
backend off renders a page whose every call 404s; the reverse leaves a working
API with no way to reach it.

| Variable | Default | What it does |
|---|---|---|
| `STRIPE_ENABLED` | `false` | Billing: plans, subscriptions, add-ons, invoices, the webhook. |
| `SOCIAL_AUTH_ENABLED` | `false` | Google and LinkedIn sign-in. A provider's button appears only when its key is configured. |
| `ORGANIZATIONS_ENABLED` | `false` | The B2B shape: organizations, per-org roles, invitations, seat limits. |
| `API_KEYS_ENABLED` | `false` | Long-lived credentials for CLIs and server-to-server calls. |
| `AUDIT_LOG_ENABLED` | `false` | An append-only record of security-relevant actions. |
| `TWO_FACTOR_ENABLED` | `false` | TOTP second factor, with recovery codes. |
| `UPLOADS_ENABLED` | `false` | Avatars and a reusable attachment model. |

The GDPR data export has no flag: portability is the other half of the erasure
the template already implements.

## MCP server

Exposes the application's capabilities as MCP tools, so an agent can act as
whoever's credential it sends. The endpoint is mounted beside Django rather
than inside its URLconf, because the transport is ASGI-only.

**No `VITE_` twin, unlike every other flag.** The rule exists because a UI
whose backend is off renders a page that 404s — and this flag gates no UI. If
you add one, add the twin with it.

| Variable | Default | What it does |
|---|---|---|
| `MCP_SERVER_ENABLED` | `false` | Mounts the endpoint. Off by default: making an application agent-callable is a decision to take deliberately. |
| `MCP_SERVER_NAME` | *(follows `API_TITLE`)* | What a client shows in its list of connected servers. |
| `MCP_MOUNT_PATH` | `/mcp` | Where the endpoint is mounted. Changing it means reconfiguring every connected client. |

## MCP OAuth

Validates OAuth 2.1 access tokens. **It never issues them.** RFC 9728 splits
the two roles and MCP's auth spec adopts the split: everything genuinely
dangerous — authorize, consent, code exchange, PKCE, redirect-URI matching,
token signing, key rotation — belongs to the *authorization server*, which is
not this application. This side is a *resource server*: it verifies a token
and publishes where its authorization server is.

That is why there is no OAuth server library in `requirements/`. `PyJWT` and
`cryptography` were already installed, and verification is all this side does.
`apps/mcp_oauth/validation.py` is under a hundred lines, and
`apps/mcp_oauth/tests/test_validation.py` attacks every one of them.

**Independent of `MCP_SERVER_ENABLED`.** The MCP endpoint forwards whatever
`Authorization` header it is given, so it works on API keys alone; and bearer
tokens are useful to the REST API whether or not MCP is on. Turning this flag
on adds `BearerTokenAuthentication` to `DEFAULT_AUTHENTICATION_CLASSES`, which
is what gives the MCP endpoint token auth for free — there is no second auth
path to keep in step.

**`MCP_OAUTH_ISSUER` and `MCP_OAUTH_AUDIENCE` have no defaults, and the app
refuses to boot without them when the flag is on.** Both are compared against a
claim in every token. Comparing against an empty string would accept a token
that carried one, and that failure is silent — the endpoint would look like it
was working perfectly while accepting anybody's token. Refusing to boot is the
loud version.

**Two deliberate deviations from house convention**, both pinned by tests so
nobody tidies them away:

- `/.well-known/oauth-protected-resource` returns the **raw RFC 9728
  document**, not the `{status, message, data, errors}` envelope. A compliant
  client parses it directly and looks for `authorization_servers` at the top
  level.
- `BearerTokenAuthentication` goes **first** in
  `DEFAULT_AUTHENTICATION_CLASSES`, not last. DRF builds the
  `WWW-Authenticate` header from `authenticators[0]` alone;
  `SessionAuthentication` offers none, so with it first DRF answers 403 with no
  challenge and the `resource_metadata` discovery hint never reaches the
  client. Anonymous API requests therefore answer 401 rather than 403 when this
  flag is on.

| Variable | Default | What it does |
|---|---|---|
| `MCP_OAUTH_ENABLED` | `false` | Accepts OAuth bearer tokens. Requires an authorization server to point at. |
| `MCP_OAUTH_ISSUER` | *(required)* | The authorization server's identifier, matched against `iss` exactly. |
| `MCP_OAUTH_AUDIENCE` | *(required)* | This resource server's identifier, matched against `aud` exactly. The check that matters most: a token minted for another resource must be refused, or this application is a confused deputy for every service sharing the issuer. |
| `MCP_OAUTH_JWKS_URL` | *(`ISSUER` + `/.well-known/jwks.json`)* | Where the signing keys are published. |
| `MCP_OAUTH_JWKS_CACHE_SECONDS` | `300` | How long a fetched key set is trusted. Bounded, so a rotation is picked up without a restart. |
| `MCP_OAUTH_SUBJECT_CLAIM` | `sub` | The claim carrying the Django user's identifier. |
| `MCP_OAUTH_USER_LOOKUP_FIELD` | `pk` | The field it is looked up by. A token for an unknown subject is refused, never used to create an account. |
| `MCP_OAUTH_WRITE_SCOPE` | `mcp:write` | The scope an unsafe method requires. Mirrors the API-key read/write split: a token without it is read-only. Set empty to let any valid token write. |
| `MCP_OAUTH_SCOPES_SUPPORTED` | `mcp:read,mcp:write` | Advertised in the metadata document, so a client knows what to ask for. |

### What the authorization server has to be

Anything that issues RS256/ES256 JWTs carrying `iss`, `aud`, `sub`, `iat` and
`exp`, and publishes a JWKS endpoint. Ory Hydra is the intended pairing because
it deliberately does *not* manage users — it runs the protocol and delegates
login and consent to the application, which is this shape exactly: Django
already owns users, sessions and two-factor, so there is no directory to sync
and an enrolled user gets their second factor on the OAuth login for free.
Keycloak, Auth0, Okta and Entra all work too; they simply want to own the
directory as well.

Wiring one up is a deployment task, not a code change — nothing in
`apps/mcp_oauth` is Hydra-specific.

## Organizations

| Variable | Default | What it does |
|---|---|---|
| `INVITATION_EXPIRY_DAYS` | `7` | How long an invitation stays redeemable. |

## API keys

| Variable | Default | What it does |
|---|---|---|
| `THROTTLE_API_KEY` | `10000/day` | Machine traffic gets its own budget rather than spending the interactive user's `THROTTLE_USER`. |

## Audit log

| Variable | Default | What it does |
|---|---|---|
| `AUDIT_LOG_RETENTION_DAYS` | `365` | What `manage.py prune_audit_log` considers expired. Nothing expires on its own — schedule the command if the table's growth matters. |

## Two-factor

| Variable | Default | What it does |
|---|---|---|
| `TWO_FACTOR_PENDING_TIMEOUT` | `300` | Seconds a half-finished login stays verifiable. |
| `TWO_FACTOR_SECRET_KEY` | *(falls back to `SECRET_KEY`)* | Encrypts TOTP secrets at rest. **Set it separately if you will ever rotate `SECRET_KEY`** — rotating a shared key locks every enrolled user out of their own account. |

## Uploads

The default filesystem backend is a **development convenience only**.
Container filesystems are ephemeral, so on any managed host every uploaded file
disappears on the next deploy, silently, leaving rows pointing at nothing.
Setting `AWS_STORAGE_BUCKET_NAME` swaps in S3, which is what a deployment
needs.

| Variable | Default | What it does |
|---|---|---|
| `AWS_STORAGE_BUCKET_NAME` | *(empty)* | Setting it switches storage to S3. The bucket stays private and URLs are signed. |
| `AWS_S3_REGION_NAME` | *(falls back to `AWS_SES_REGION_NAME`, then `us-east-1`)* | |
| `AWS_S3_ENDPOINT_URL` | *(none)* | For S3-compatible storage: MinIO, Cloudflare R2, DigitalOcean Spaces. |
| `UPLOAD_ALLOWED_TYPES` | `image/jpeg,image/png,image/gif,image/webp,application/pdf` | Sniffed from the file's own bytes — never the Content-Type header or the extension. |
| `UPLOAD_MAX_BYTES` | `5242880` (5 MiB) | Rejected above this. |
| `UPLOAD_URL_EXPIRY_SECONDS` | `300` | How long a signed download URL stays usable. |

## Billing

| Variable | Default | What it does |
|---|---|---|
| `STRIPE_SECRET_KEY` | *(none)* | Server-side Stripe key. |
| `STRIPE_PUBLISHABLE_KEY` | *(none)* | Client-side key. Card details are entered on Stripe's hosted page and never touch this app. |
| `STRIPE_WEBHOOK_SECRET` | *(none)* | Verifies the webhook signature. That check is the **only** thing authenticating the one CSRF-exempt, unauthenticated endpoint in the project. |
| `STRIPE_SUCCESS_URL` | `{FRONTEND_URL}/subscription/success` | Where Checkout returns on success. |
| `STRIPE_CANCEL_URL` | `{FRONTEND_URL}/subscription/cancel` | And on cancel. |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | `14` | Days a lapsed subscription keeps working before access is cut off. |

## Social login

The default python-social-auth pipeline hands a social identity any existing
account with the same email. **That is disabled here**, because anyone who can
get a provider to assert an address would take over the account.

| Variable | Default | What it does |
|---|---|---|
| `GOOGLE_OAUTH2_KEY` | *(none)* | A provider's button is offered to the frontend only when its key is set, so a button never appears for one that would fail on the redirect. |
| `GOOGLE_OAUTH2_SECRET` | *(none)* | |
| `LINKEDIN_OAUTH2_KEY` | *(none)* | |
| `LINKEDIN_OAUTH2_SECRET` | *(none)* | |

## Rate limiting

Format is DRF's: `<number>/<period>`, where period is `second`, `minute`,
`hour` or `day`.

| Variable | Default | What it does |
|---|---|---|
| `THROTTLE_ANON` | `100/day` | Unauthenticated callers. |
| `THROTTLE_USER` | `1000/day` | Signed-in callers. |
| `THROTTLE_LOGIN` | `10/min` | Login and second-factor verification. |
| `THROTTLE_PASSWORD_RESET` | `5/hour` | Reset requests. |
| `THROTTLE_DATA_EXPORT` | `3/day` | Building an export walks every table the user touches and sends mail — expensive, and enumerable. |
| `PASSWORD_RESET_TIMEOUT` | `259200` (3 days) | How long reset and verification links stay valid, in seconds. |
| `GDPR_EXPORT_LINK_TIMEOUT` | `86400` (1 day) | How long an export download link stays usable, in seconds. |

## Cookies, CORS and CSRF

Development leaves these alone: the Vite dev server proxies `/api` to Django,
so the SPA and the API are same-origin and `Lax` cookies work. Set them when
the frontend is served from a different origin.

| Variable | Default | What it does |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `[FRONTEND_URL]` (dev also adds the localhost:3000 variants) | Origins allowed to make credentialed requests. |
| `CSRF_TRUSTED_ORIGINS` | `[FRONTEND_URL]` | Origins Django accepts unsafe requests from. |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `None` requires `Secure=true` in every current browser. |
| `CSRF_COOKIE_SAMESITE` | `Lax` | |
| `SESSION_COOKIE_SECURE` | `true` (dev: `false`) | |
| `CSRF_COOKIE_SECURE` | `true` (dev: `false`) | |

## Production hardening

Read only by `production.py`.

| Variable | Default | What it does |
|---|---|---|
| `SECURE_SSL_REDIRECT` | `true` | |
| `USE_X_FORWARDED_PROTO` | `true` | Set `false` only if the app terminates TLS itself rather than sitting behind a proxy that sets `X-Forwarded-Proto`. |
| `SECURE_HSTS_SECONDS` | `31536000` (1 year) | |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `true` | |
| `SECURE_HSTS_PRELOAD` | `true` | |

## Error tracking

Setting `SENTRY_DSN` is the only thing that turns this on — there is no
separate flag, and nothing is imported without it. It is never armed during a
test run, so a DSN in a CI environment cannot fill a real project with noise.

| Variable | Default | What it does |
|---|---|---|
| `SENTRY_DSN` | *(empty)* | The project to report to. Empty means Sentry is not imported at all. |
| `SENTRY_RELEASE` | *(platform commit SHA)* | Tags tracebacks with a commit rather than just "production". Railway and Render supply their own; set this only if neither applies. |
| `SENTRY_SEND_PII` | `false` | Off on purpose: turning it on ships email addresses, usernames and IP addresses to a third party. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Performance sampling, 0.0 to 1.0. Costs quota, so opt in deliberately. |

## Serving

| Variable | Default | What it does |
|---|---|---|
| `PORT` | `8000` | The port gunicorn binds to. Managed hosts inject this themselves. |
| `WEB_CONCURRENCY` | `3` | gunicorn worker count. The workers are uvicorn's ASGI class; gunicorn still supervises them. |
| `SERVE_SPA` | *(whether `website/dist/index.html` exists)* | Whether Django serves the built SPA. On in the container, off locally where the Vite dev server serves it instead. Pinned off in `testing.py` so the URLconf does not depend on whether someone has run a frontend build. |

## Local development

| Variable | Default | What it does |
|---|---|---|
| `ENABLE_DEBUG_TOOLBAR` | `true` in development | django-debug-toolbar. |
| `DEBUGPY` | *(unset)* | Set `1` to have `runserver` wait for a debugger. It is opt-in because it used to be unconditional, and hung every `runserver`. |
| `DEBUGPY_PORT` | `5678` | |
| `DJANGO_SUPERUSER_USERNAME` | *(none)* | The entrypoint creates a superuser on container start. A **no-op unless all three** are set. |
| `DJANGO_SUPERUSER_EMAIL` | *(none)* | |
| `DJANGO_SUPERUSER_PASSWORD` | *(none)* | |

---

## Frontend

These live in `website/.env` and are **inlined into the bundle at build time**.
In Docker they are `--build-arg`s, not runtime environment variables: changing
one on a deployed container does nothing until the image is rebuilt.

| Variable | Default | What it does |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Where the SPA sends requests. **Must not end in a slash.** |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Where the Vite dev server proxies `/api`. Development only; never reaches the bundle. |
| `VITE_STRIPE_ENABLED` | `false` | Must match `STRIPE_ENABLED`. |
| `VITE_STRIPE_PUBLISHABLE_KEY` | *(none)* | |
| `VITE_SOCIAL_AUTH_ENABLED` | `false` | Must match `SOCIAL_AUTH_ENABLED`. |
| `VITE_ORGANIZATIONS_ENABLED` | `false` | Must match `ORGANIZATIONS_ENABLED`. |
| `VITE_API_KEYS_ENABLED` | `false` | Must match `API_KEYS_ENABLED`. |
| `VITE_AUDIT_LOG_ENABLED` | `false` | Must match `AUDIT_LOG_ENABLED`. |
| `VITE_TWO_FACTOR_ENABLED` | `false` | Must match `TWO_FACTOR_ENABLED`. |
| `VITE_UPLOADS_ENABLED` | `false` | Must match `UPLOADS_ENABLED`. |

**Not an environment variable:** the product name, colours, type and shape come
from `website/src/styles/brand.ts`. See [Theming](../README.md#theming).

---

## Supplied by the platform

Read but never set by you. They exist so a first deploy boots before the domain
is known.

| Variable | Read by | What it does |
|---|---|---|
| `RAILWAY_PUBLIC_DOMAIN` | `production.py` | Seeds `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL`. |
| `RENDER_EXTERNAL_HOSTNAME` | `production.py` | The same, on Render. |
| `FLY_APP_NAME` | `production.py` | The same, on Fly. |
| `RAILWAY_GIT_COMMIT_SHA` | `base.py` | Tags Sentry releases. |
| `RENDER_GIT_COMMIT` | `base.py` | The same, on Render. |
| `DJANGO_SETTINGS_MODULE` | everything | Set by `manage.py`, the ASGI entrypoint or CI — not by a `.env` file. |
| `DB_ENGINE` | `testing.py` | CI sets it to `postgres` to point the suite at a real database instead of SQLite. |
