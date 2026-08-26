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

Install the git hooks once so formatting, lint and secret-scanning problems
are caught before they reach CI:

```bash
pre-commit install
```

The hooks include [ggshield](https://github.com/GitGuardian/ggshield), which
scans staged changes for hardcoded secrets. It needs an API key:

```bash
export GITGUARDIAN_API_KEY=...   # dashboard.gitguardian.com -> API -> Personal access tokens
```

Without the key the hook fails rather than silently passing, which is the
behaviour you want from a security check. Like any pre-commit hook it can be
skipped with `git commit --no-verify` -- it is a fast local net, not the gate.
The gate is the required status check on `main`.

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

## Branch protection

`main` is protected, and these settings are part of the template's contract
rather than one repository's preference. If you adopt this template,
reproduce them under **Settings -> Branches** (or **Rules -> Rulesets**):

- **Require a pull request before merging.** Without this, a direct push
  bypasses the security scan entirely -- GitGuardian runs on `pull_request`
  events, so anything pushed straight to `main` is never scanned.
- **Require status checks to pass**, with *Require branches to be up to date*.
  Required: `GitGuardian Security Checks`, `Backend`, `Frontend`,
  `Docker image`, `Source is tracked`.
- **Do not allow bypassing the above settings**, including for admins.

That last one is deliberate. It means clearing a security finding is a
conscious trip into repository settings, not a button on the pull request
page -- a human decides when a finding is acceptable, and the decision leaves
a trace.

A check only becomes selectable once it has reported on the repository at
least once, so open one pull request before configuring the list.

## Handling a GitGuardian failure

Do not merge. Open the incident from the check's **Details** link and decide:

- **A real secret** -- rotate it first, then remove it from the code. Rotation
  comes first because the value is already exposed; deleting the line does not
  un-expose it.
- **A false positive** -- a placeholder, a fixture, a local-only default --
  mark it as such in the GitGuardian dashboard. That triage is the human
  judgement the gate exists to preserve; do not work around it by disabling
  the check.

## Commit messages

Describe what changed and why. A subject line under about 72 characters, then
a blank line, then the detail. Reference an issue if there is one.

## Reporting a security issue

Please do not open a public issue for a security problem. Email the
maintainer instead.

## Optional: MCP tooling for your assistant

`.mcp.json` at the repository root configures MCP servers for a coding
assistant working on this repository — the compose Postgres (read-only) and
the filesystem. It is **entirely optional**: nothing in the application reads
it, no test depends on it, and you can delete it without consequence.

It is unrelated to `apps/mcp_server` and `apps/mcp_client`, which are product
features. See [docs/mcp.md](docs/mcp.md) for which is which.

Read-only Postgres is deliberate. An assistant that can read the schema
answers most questions; one that can write to your development database can
lose an afternoon of fixtures without meaning to. Change it if you disagree —
but change it knowingly.
