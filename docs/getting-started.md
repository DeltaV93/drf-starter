# Getting started

What you need installed, what you need to configure, and what you need to sign
up for — in the order you need them.

The short version: **development needs no configuration at all**, and
**production needs four variables**. Everything else in the 100-plus-line
`.env.example` is optional, and this guide is mostly about telling you which
parts you can ignore.

- [Running it locally](#running-it-locally)
- [The four variables production needs](#the-four-variables-production-needs)
- [Services you may need to sign up for](#services-you-may-need-to-sign-up-for)
- [Turning features on](#turning-features-on)
- [The trap: boots ≠ works](#the-trap-boots--works)
- [Deploying](#deploying)
- [When something is wrong](#when-something-is-wrong)

For the exhaustive list of every variable and its default, see
[configuration.md](configuration.md). This document is the subset you actually
have to think about.

---

## Running it locally

### What you need installed

| | Version | Why |
|---|---|---|
| Python | 3.11+ | `pyproject.toml` sets the floor; CI runs 3.14 |
| Node | 20+ | CI and the Docker build run 26 |
| Docker | any recent | Only if you use `make up` |
| PostgreSQL | 16 | Only if you are *not* using Docker |
| Redis | 7 | Only if you are *not* using Docker — **and you do need it**, see below |

### With Docker — the short path

```bash
git clone <your-repo-url> && cd <your-repo>
cp .env.example .env
cp website/.env.example website/.env
make up
```

That starts Postgres, Redis, Django and a Celery worker. The API is on
http://localhost:8000, the docs on http://localhost:8000/api/docs/.

The frontend runs separately:

```bash
make fe-install
make fe-dev          # http://localhost:3000
```

**You do not have to edit `.env` first.** In development `SECRET_KEY`
generates itself if unset, and every other default points at the compose
services. The copied file is there so you have somewhere to put things later.

> One consequence of the generated key: it changes on every restart, which
> invalidates sessions and any password-reset link you were mid-way through
> testing. Set `SECRET_KEY` in `.env` once and that stops.

### Without Docker

```bash
make setup       # virtualenv, dependencies, both .env files
make migrate
make run         # http://localhost:8000

make fe-install
make fe-dev      # http://localhost:3000
```

You supply Postgres and Redis yourself. The defaults expect Postgres on
`localhost:5432` with database `app`, user `postgres`, password `postgres` —
`docker-compose.yml` is the reference if you would rather match it exactly.

### Redis is not optional in development

This is the one that costs people an hour.

`CACHES` points at Redis in every environment except the test suite, and DRF's
throttles read the cache on every request that reaches a view. With Redis down,
**logging in returns a 500** — not a warning, not a degraded mode. The
traceback says `ConnectionRefused` on port 6379 and says nothing about
throttling, so it does not look like a cache problem.

`make up` starts Redis for you. Running without Docker, start it before you
start Django.

If you genuinely cannot run Redis, point the cache at memory in a local
settings module — but know that you are then not exercising throttling at all.

### Then make it yours

The Django package ships as `template`. Rename it before you build anything on
top:

```bash
python scripts/rename_project.py myapp --dry-run    # see what it would touch
make rename NAME=myapp                              # do it
```

This rewrites every reference and substitutes the display name in the API docs
and the UI. It refuses to run on a dirty working tree, so commit first. Then
delete the script — a project only gets renamed once.

---

## The four variables production needs

Verified by booting production settings with an empty environment and adding
one variable at a time until it started:

| Variable | Example | What breaks without it |
|---|---|---|
| `SECRET_KEY` | 50+ random characters | Refuses to start. **No fallback, on purpose** — a default here would be a published key |
| `ALLOWED_HOSTS` | `example.com,www.example.com` | Refuses to start |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | Refuses to start rather than retrying against localhost |
| `FRONTEND_URL` | `https://example.com` | Refuses to start. It is the base for reset and verification links, and the default for CORS and CSRF origins |

Generate a key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Each of the four refuses to boot with a message naming itself and saying what
it is for. That is deliberate: every one of them fails *silently and later* if
it defaults to something plausible.

**On Railway, Render and Fly it is two, not four.** Those platforms inject
their own domain, and `production.py` derives `ALLOWED_HOSTS` and
`FRONTEND_URL` from it — so a first deploy boots before you own a domain. Set
`SECRET_KEY` and `DATABASE_URL` and you are up. Override the other two later
when you point a real domain at it.

> `FRONTEND_URL` needs the scheme. `example.com` without `https://` passes the
> boot check and then fails CORS validation at runtime with an error about
> `corsheaders.E013` that does not mention the variable.

Everything else has a working default. You do not need to read the rest of
this document to deploy.

---

## Services you may need to sign up for

Nothing here is required. Each is needed only for the feature beside it.

| Service | Needed for | What you set |
|---|---|---|
| **PostgreSQL** | always | `DATABASE_URL` |
| **Redis** | always | `REDIS_URL` — cache, Celery broker, throttling |
| **AWS SES** | real email | `EMAIL_BACKEND=django_ses.SESBackend`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SES_REGION_NAME`, `DEFAULT_FROM_EMAIL` |
| **Stripe** | billing | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` |
| **AWS S3** (or R2/MinIO/Spaces) | uploads in production | `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, optionally `AWS_S3_ENDPOINT_URL` |
| **Google / LinkedIn OAuth apps** | social login | `GOOGLE_OAUTH2_KEY` / `_SECRET`, `LINKEDIN_OAUTH2_KEY` / `_SECRET` |
| **Sentry** | error tracking | `SENTRY_DSN` — the only thing that turns it on; there is no flag |
| **An OAuth authorization server** (Ory Hydra, Auth0, Keycloak, Okta, Entra) | MCP over OAuth | `MCP_OAUTH_ISSUER`, `MCP_OAUTH_AUDIENCE` |
| **Anthropic API key** | outbound MCP calls | `ANTHROPIC_API_KEY`, `MCP_CLIENT_MODEL` |

**In development you need none of them.** Email prints to the console,
uploads go to the local filesystem, and every feature that needs a third party
is off by default.

### Email is the one worth setting up early

Registration, email verification and password reset all send mail. In
development they print to the terminal, which is fine — but it means the
first time you exercise those flows for real is in production, against SES
credentials nobody has tested.

SES also starts in a sandbox that only delivers to verified addresses.
Requesting production access takes a day or two, so ask before you need it.

---

## Turning features on

Eleven features are off by default. Each one is a flag, and most of them need a
`VITE_` twin so the UI matches the API.

| Flag | Gives you | Also set |
|---|---|---|
| `ORGANIZATIONS_ENABLED` | Teams, roles, invitations, seat limits | `VITE_ORGANIZATIONS_ENABLED` |
| `API_KEYS_ENABLED` | Hashed, scoped, expiring machine credentials | `VITE_API_KEYS_ENABLED` |
| `AUDIT_LOG_ENABLED` | Append-only record of security-relevant actions | `VITE_AUDIT_LOG_ENABLED` |
| `TWO_FACTOR_ENABLED` | TOTP with recovery codes | `VITE_TWO_FACTOR_ENABLED`, `TWO_FACTOR_SECRET_KEY` |
| `UPLOADS_ENABLED` | File uploads | `VITE_UPLOADS_ENABLED`, plus S3 in production |
| `STRIPE_ENABLED` | Billing | `VITE_STRIPE_ENABLED`, `VITE_STRIPE_PUBLISHABLE_KEY`, the three Stripe keys |
| `SOCIAL_AUTH_ENABLED` | Google / LinkedIn login | `VITE_SOCIAL_AUTH_ENABLED`, provider keys |
| `EMAIL_ASYNC` | Send mail through Celery | A running worker |
| `MCP_SERVER_ENABLED` | The app as tools an agent can call | — |
| `MCP_OAUTH_ENABLED` | OAuth bearer tokens | `MCP_OAUTH_ISSUER`, `MCP_OAUTH_AUDIENCE` |
| `MCP_CLIENT_ENABLED` | The app calling other MCP servers | `VITE_MCP_CLIENT_ENABLED`, `ANTHROPIC_API_KEY`, `MCP_CLIENT_MODEL` |

**The `VITE_` twins are not optional.** They are read at *build* time by Vite,
in a different language, at a different moment — nothing links them to the
backend flag automatically. Out of step, the UI renders a page whose every API
call 404s, and it looks like a broken feature rather than a missing variable.

A test enforces that every backend flag *has* a twin. Nothing can enforce that
you set both to the same value.

### On removing rather than disabling

Every optional feature can be deleted outright — no feature holds a foreign key
into another. The README has a "Removing it" block per feature. If you know you
will never want billing, deleting `apps/subscriptions` is cleaner than carrying
a flag forever.

---

## The trap: boots ≠ works

This is the part that costs the most time, so it gets its own section.

**Turning a flag on with none of its credentials boots perfectly.** I checked
each one: `STRIPE_ENABLED=true` with no Stripe keys starts, serves, and passes
`manage.py check`. It fails when somebody clicks Subscribe.

| Flag on, credentials missing | What happens |
|---|---|
| `STRIPE_ENABLED` | Boots. Fails at checkout |
| `SOCIAL_AUTH_ENABLED` | Boots. No provider buttons appear — the frontend only offers providers whose key is configured, so this fails *quietly* |
| `UPLOADS_ENABLED` | Boots, and works, on the local filesystem — **which is ephemeral on every managed host**. Files vanish on the next deploy, leaving rows pointing at nothing |
| `EMAIL_ASYNC` with no worker | Boots. Mail queues and is never sent |
| `MCP_CLIENT_ENABLED` | Boots. Fails on the first outbound call |
| `MCP_OAUTH_ENABLED` | **Refuses to boot** — the one that fails loudly, because its two variables are compared against a claim in every token and an empty comparison would accept anybody's |

The one to watch is `UPLOADS_ENABLED`, because it appears to work. The
filesystem backend is a development convenience; set `AWS_STORAGE_BUCKET_NAME`
before anyone uploads anything they expect to keep.

`TWO_FACTOR_SECRET_KEY` deserves a note too. It falls back to `SECRET_KEY`, so
two-factor works without it — until you rotate `SECRET_KEY`, at which point
every enrolled user's secret becomes undecryptable and they are locked out of
their own accounts. Set it separately, once, before anyone enrols.

---

## Deploying

The container serves ASGI:

```
gunicorn template.asgi:application -k uvicorn.workers.UvicornWorker
```

Uvicorn rather than a plain WSGI worker because the MCP transport is ASGI-only.
Django is unaffected — every middleware is sync, so the chain is adapted once.

Checks worth running before you ship:

```bash
make check      # Django checks + the production deploy checklist + missing migrations
make test
make lint
```

`make check` runs `manage.py check --deploy --fail-level WARNING` against
production settings with throwaway values, so it catches a security
misconfiguration without needing a real production `.env`.

### Things that bite on a first deploy

- **Migrations are committed and must stay that way.** With a custom user model
  a fresh clone cannot `migrate` without them.
- **Health probes** answer at `/api/v1/health/` before the SSL redirect and
  before host validation, so a platform probing over plain HTTP with its own
  Host header gets a 200 rather than a 301.
- **The SPA is served by WhiteNoise from the same container** when
  `website/dist` exists. No separate static host, no CDN required.
- **Set `WEB_CONCURRENCY`** to match the instance size. It defaults to 3.

---

## When something is wrong

| Symptom | Cause |
|---|---|
| 500 on login, locally | Redis is not running |
| `SECRET_KEY must be set` | You are in production settings without one — that is the check working |
| `corsheaders.E013` | `FRONTEND_URL` is missing its `https://` |
| Connection refused to `127.0.0.1:5432` in production | `DATABASE_URL` is unset. On Railway, adding the Postgres service does not inject it — reference `${{Postgres.DATABASE_URL}}` in the web service's variables |
| A page renders, then every call 404s | A backend flag is on and its `VITE_` twin is off, or the reverse |
| White screen, no server error | A JavaScript asset 404'd and the SPA catch-all returned HTML for it. Check the network tab, not the server log |
| A feature "does nothing" | Its flag is on and its credentials are missing. See [boots ≠ works](#the-trap-boots--works) |

### The configuration reference cannot drift

`docs/configuration.md` and both `.env.example` files are checked against the
source in **both directions** by `apps/core/tests/test_env_documented.py`. A
variable the code reads but nothing documents fails the build; so does a
variable documented but read by nothing.

That machinery has one blind spot worth knowing about: a variable read by a
*dependency* rather than by this repository is invisible to it.
`ANTHROPIC_API_KEY` was exactly that — required, and documented nowhere — until
`clients/base.py` was changed to read it explicitly. If you add a library that
reads its own environment variable, read it yourself and pass it in, or it
will not appear in any of these lists.
