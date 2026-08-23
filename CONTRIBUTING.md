# Contributing

Thanks for helping improve this template.

## Getting set up

```bash
make setup          # virtualenv, dependencies, .env files
make migrate
make run            # http://localhost:8000

cd website && npm install && npm run dev   # http://localhost:3000
```

Or run everything in containers with `make up`.

Install the git hooks once so formatting and lint problems are caught before
they reach CI:

```bash
pre-commit install
```

## Before you open a pull request

```bash
make lint     # ruff + eslint + tsc
make test     # pytest + vitest
make check    # Django checks, including the production deploy checklist
```

CI runs the same commands plus a Postgres run, a run with billing disabled,
and a Docker build. Getting these three green locally means CI usually is too.

## Conventions

**Python.** Formatted and linted by ruff; the config lives in
`pyproject.toml`. Single quotes, 95-column lines. Run `make format` rather
than fixing style by hand.

**TypeScript.** ESLint flat config in `website/eslint.config.js`. Warnings
fail the build (`--max-warnings 0`), so fix them rather than suppressing them.

**Migrations are tracked.** Never add `apps/*/migrations/` to `.gitignore` --
with a custom user model, a fresh clone cannot run `migrate` without them.
Run `make migrations` after changing a model and commit the result. CI fails
on missing migrations.

**Settings.** Anything that differs between deployments comes from the
environment. Add the variable to `.env.example` in the same change, with a
comment saying what it does. Never commit a real secret.

**Tests.** New behaviour needs a test. Name tests after the behaviour rather
than the function (`test_login_does_not_reveal_whether_the_account_exists`
beats `test_login_2`). Backend tests default to SQLite for speed; CI also runs
them against Postgres.

**The optional apps.** Billing (`STRIPE_ENABLED`) and social login
(`SOCIAL_AUTH_ENABLED`) are opt-in. A change to either must leave the project
booting and passing with the flag off -- CI checks this.

## Commit messages

Describe what changed and why. A subject line under about 72 characters, then
a blank line, then the detail. Reference an issue if there is one.

## Reporting a security issue

Please do not open a public issue for a security problem. Email the
maintainer instead.
