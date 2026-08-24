# Repository conventions

Read this before changing anything. It records decisions that are easy to
undo by accident.

## Layout

- `apps/` — Django apps. `core` (health, throttles), `users` (the user model),
  `authentication` (auth views), `subscriptions` (billing, optional).
- `template/` — the project package: settings, urls, wsgi/asgi, celery.
  Renamed by `scripts/rename_project.py` when someone adopts the template.
- `utils/` — helpers not tied to one app: the response envelope, email,
  logging, GDPR anonymization.
- `website/` — the React SPA.

## Commands

```bash
make test     # pytest + vitest
make lint     # ruff check + ruff format --check + eslint + tsc
make format   # auto-fix both
make check    # django checks + production deploy checklist + missing migrations
```

Use the `.venv/bin/` binaries directly if you are not going through make.
Backend tests run against SQLite by default: `pytest` needs no services.

## Things not to undo

**Migrations are tracked.** `apps/*/migrations/` must never go back into
`.gitignore`. With a custom `AUTH_USER_MODEL`, a fresh clone cannot
`migrate` without them — that was the single biggest reason the template did
not work. Run `make migrations` after a model change and commit the result.

**CSRF middleware stays enabled.** `django.middleware.csrf.CsrfViewMiddleware`
was commented out in `MIDDLEWARE`. Session auth without it is not session
auth. The contract is pinned by `apps/authentication/tests/test_csrf.py`.

**The Stripe webhook is the only csrf_exempt view.** Its signature check is
what authenticates it. Do not add `csrf_exempt` anywhere else.

**`SECRET_KEY` fails loudly outside development.** Do not add a fallback.

**Logging goes to stdout.** No `FileHandler` in any settings module.

**`HealthCheckMiddleware` stays ahead of `SecurityMiddleware`.** It has to
run before the SSL redirect and before anything calls `request.get_host()`,
or platform health probes get a 301 or a 400 instead of the 200 they need —
which is what broke the first Railway deploy's healthcheck. It is first in
`base.py` and `production.py`; development inserts `debug_toolbar` ahead of
it, which is harmless because what matters is the position relative to
`SecurityMiddleware`. `production.py` rebuilds the list to insert WhiteNoise
and must keep the ordering. `apps/core/tests/test_health_probes.py` pins the
behaviour and the ordering in every environment.

**The SPA catch-all stays last in `urlpatterns`** and must keep excluding
`api/`, `admin/`, `static/` and `media/`. Widen it and every endpoint starts
answering with `index.html` and a 200, which nothing else would catch.
`apps/core/tests/test_spa.py` pins it.

**`SERVE_SPA` is pinned off in `testing.py`.** It otherwise defaults to
whether `website/dist` exists, which would make the test URLconf depend on
whether someone had run a frontend build.

**Visual values live in `website/src/styles/brand.ts`, nowhere else.** No
component hardcodes a colour, radius or font, which is what makes a re-brand
one file. `styles/theme.ts` derives the MUI theme and has no literals of its
own. The two exceptions cannot read a token and say so where they live:
`public/favicon.svg`, fetched before any JavaScript runs, and `index.html`,
which gets its title and theme colours substituted at build time by the
`brandHtml()` plugin in `vite.config.ts`.

**The colour-scheme attribute is named in two places and must match.** The
inline script in `index.html` sets `data-mui-color-scheme` on `<html>` before
the bundle loads, which is the only thing preventing a white flash for a
returning dark-mode visitor; `colorSchemeSelector` in `theme.ts` is what the
stylesheet keys off. Change one and the flash returns silently -- the app
still works, it just blinks. `styles/theme.test.ts` reads the HTML and pins
them together.

**TypeScript stays below 7 until typescript-eslint supports it.** Dependabot
will keep proposing 7.x. `tsc` itself passes on it, which is what makes the
bump look safe -- but typescript-eslint refuses to load against the TS 7 API
and `npm run lint` dies before it checks a single file, so the React Compiler
rules stop running. 6.0.x is the highest version the whole toolchain agrees
on. Revisit when typescript-eslint ships TS >=7.1 support.

**A new view needs a declared request and response.** `@extend_schema` with
only a `summary` leaves drf-spectacular guessing, and it cannot guess for a
plain `APIView`. CI runs `spectacular --fail-on-warn`, so an undocumented view
fails the build; `make check` runs the same thing, so it fails locally first.
`apps/core/tests/test_openapi_schema.py` pins the parts of the schema that
carry meaning.

**`manage.py` does not attach a debugger by default.** It used to call
`pydevd_pycharm.settrace()` unconditionally, which hung every `runserver`.
Remote debugging is opt-in via `DEBUGPY=1`.

## Merging

**Green means every check run, not every workflow job.**
`/actions/runs/{id}/jobs` returns only this repository's own workflow.
Third-party App checks -- GitGuardian among them -- appear solely in
`/commits/{sha}/check-runs`. A PR was once merged here with GitGuardian
failing because only the workflow's jobs were inspected, and the security
check was invisible to everything being watched.

Before merging, read `/commits/{sha}/check-runs` and confirm every entry is
`success`. Never merge past a failing security check: a human decides when a
finding is acceptable, and the decision belongs in the GitGuardian dashboard,
not in a merge.

`main` requires a pull request, so do not push to it directly -- GitGuardian
runs on `pull_request` events only, and a direct push is never scanned.

## Settings

Split by environment under `template/settings/`, selected by
`DJANGO_ENVIRONMENT`. `template/settings/__init__.py` only acts as a loader
when it *is* the settings module — importing `template.settings.testing`
directly must not pull in the development environment as a side effect.

Anything that varies between deployments comes from the environment via
`env_bool` / `env_list` / `env_int` in `base.py`. Add new variables to
`.env.example` in the same change.

`DATABASE_URL` wins over the individual `DB_*` variables when set, because
that is what managed hosts inject. `production.py` also derives
`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` from the
platform's domain variable, so a first deploy boots before the domain is
known.

## Optional apps

`STRIPE_ENABLED` and `SOCIAL_AUTH_ENABLED` gate `INSTALLED_APPS`, URLs and
middleware. Any change must leave the project booting and passing with the
flag off. `template/settings/testing.py` turns billing on by default (before
importing `base`, which is when the flag is read); CI runs the suite both
ways.

## API conventions

Every endpoint returns the `utils.api_utils.api_response` envelope:
`{status, message, data, errors}` with null keys dropped. Views are DRF
`APIView` subclasses — never plain Django `View`, which cannot render a DRF
`Response`.

Routes live under `/api/v1/`. Django URLs end in a slash; the frontend's
`routes.ts` preserves that, because dropping it turns every POST into an
`APPEND_SLASH` redirect that loses the body.

Endpoints that take an email address answer identically whether or not the
account exists, so they cannot be used to enumerate accounts. Keep it that
way when adding new ones.

## Frontend

The server session is the source of truth. `useAuthBootstrap` asks
`/users/me/` on load; nothing is trusted from `localStorage`.
`ProtectedRoute` waits for that answer before redirecting.

`src/lib/api.ts` is the only place that touches CSRF. Do not set
`X-CSRFToken` by hand at a call site.

ESLint runs with `--max-warnings 0`. The React Compiler rules
(`set-state-in-effect`, `incompatible-library`) catch real problems — fix the
code rather than disabling the rule.
