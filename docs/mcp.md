# MCP

Three separate things share a name in this repository. Knowing which one you
are looking at saves a lot of confusion:

| | What it is | Where | Flag |
|---|---|---|---|
| **Server** | This application, as tools an agent can call | `apps/mcp_server/` | `MCP_SERVER_ENABLED` |
| **Client** | This application calling *other people's* MCP servers | `apps/mcp_client/` | `MCP_CLIENT_ENABLED` |
| **Dev tooling** | MCP servers for an assistant working on this repo | `.mcp.json` | none — it is a file you may delete |

The first two are product features and are independent: an application can be
agent-callable without itself being an agent, and the other way round. The
third is about the repository, not the product, and nothing in the application
reads it.

Every setting named here is in [configuration.md](configuration.md).

---

## Server — this application, as tools

```
agent ──credential──▶ /mcp ──▶ tool ──▶ the application's own API ──▶ database
```

**Every tool goes through the API, not the ORM.** `apps/mcp_server/call.py`
makes a real in-process Django request — full middleware, DRF authentication,
permission classes, throttles, serializers — that never touches a socket. So
every rule the API already enforces applies to an agent for free, and an agent
cannot reach anything a user holding the same credential could not reach over
HTTP. Not by convention: there is no other path.

Querying the ORM from a tool would mean re-implementing, per tool, every rule
the API already has: who owns this row, does this credential carry write scope,
is this organization the caller's, does this action get audited. That is
exactly the code an agent must not slip past, so it is re-used by construction
rather than duplicated.

**The server holds no credential of its own.** It carries the caller's and
refuses when there is none, rather than falling back to anonymous — an empty
list reads as *"you have none of those"* rather than *"I could not tell who you
are"*. A service credential of its own would make it a confused deputy.

### Where it is mounted

Beside Django, not inside its URLconf:

```
template/asgi.py
  lifespan  ──▶ MCP app          (see "Three bugs" below — this one is load-bearing)
  /mcp/*    ──▶ MCP app
  else      ──▶ Django app       (urls.py, middleware, the SPA catch-all)
```

The SDK's transport is ASGI-only — `handle_request(scope, receive, send)`, no
WSGI entry point — which is why the whole application is served over ASGI. One
image, one deploy, no loopback.

### The tool surface

Included: `whoami`; list and get the caller's organizations and members; list
files and mint a signed download URL; read the caller's own activity; update
their profile; request a data export.

Excluded, and listed here so the exclusion is legible: subscribe, cancel or
change billing; mint or revoke API keys; remove a member; delete an account;
disable two-factor.

**The rule: if the audit log exists to record it, an agent does not get to do
it.** Those operations are not permission-checked, they simply have no tool,
which is a stronger guarantee than a check that could be wrong.
`apps/mcp_server/tests/test_tool_surface.py` pins the list, so changing it
shows up in a diff.

Adding a tool is adding an async function under `apps/mcp_server/tools/` and
naming it in `TOOLS`. The docstring becomes the description the model reads and
the signature becomes the schema, so both are load-bearing.

### Authentication

Whatever the API accepts. The endpoint forwards the caller's `Authorization`
header into the same Django stack, so it works with an API key today and with
an OAuth bearer token the moment `MCP_OAUTH_ENABLED` is on — there is no
MCP-specific auth path to keep in step.

`apps/mcp_server` imports nothing from `apps/mcp_oauth`, and a test asserts it.

### Three bugs worth knowing about

All three were found the first time a real MCP client spoke to this endpoint.
Each left a server that mounted cleanly and logged nothing alarming, and each
is now covered by a test. If you fork the transport wiring, these are the ones
to watch for:

1. **The lifespan must reach the MCP app.** The SDK's Starlette app declares
   `lifespan=session_manager.run()`, and that starts the task group every
   request is handled inside. Send the lifespan scope to Django instead —
   which raises on anything but `http` — and the server decides the app has no
   lifespan, carries on, and answers every call with *"Task group is not
   initialized"*.

2. **The Host allow-list must come from `ALLOWED_HOSTS`.** The SDK enables
   DNS-rebinding protection by default and defaults its allow-list to
   `127.0.0.1`. Correct for a local server; behind a real domain every request
   gets **421 Misdirected Request**. This one works perfectly on localhost,
   which is exactly where anyone would test it.

3. **The credential must be read per message, not per HTTP request.** The
   transport hands the message to the server loop, which runs in the
   lifespan's task — so a `ContextVar` set while handling the request is
   invisible by the time the tool runs.

---

## Client — calling other people's servers

```python
from apps.mcp_client import client_for

result = client_for('example', user=request.user).ask('What changed this week?')
```

**One file per connection.** A module under `apps/mcp_client/servers/` defines
a `SERVER = ServerDefinition(...)` and nothing else; the registry finds it by
walking the package.

The property that buys: **a server cannot become reachable without a file in
the repository describing it.** `MCP_CLIENT_SERVERS` chooses among those files
and cannot introduce one, and neither can the API — a request can say "I
authorise this server" and hand over a token, and nothing else. So the whole
set of reachable servers is auditable in a diff, and a stolen database cannot
point the application somewhere nobody approved.

### Two transports

| | `connector` | `local` |
|---|---|---|
| Who reaches the server | Anthropic | this application |
| Needs | a public HTTPS URL | anything you can reach |
| Runs the tool loop | Anthropic | this application |
| Can list tools before a call | no | yes |
| Works on Bedrock / Vertex | no | yes |

Chosen per server, in its `servers/` module — a server behind a VPC is simply
not reachable from Anthropic's side, whatever a deployment would prefer.
`clients/base.py` makes them interchangeable at the call site, so switching is
one line and no caller moves.

**`base.py` owns everything that is not "how do I reach it"**: credential
resolution, the refusal when there is none, the result shape, the audit call,
the error type. Two transports disagreeing about any of those would be two
integrations wearing one name.

### Credentials

A user's own wins over the deployment-wide one, and a server marked
`requires_user_credential` **refuses rather than falling back**. Falling back
would let a user who has authorised nothing act with the deployment's
authority — the same confused-deputy shape the server side avoids.

Stored tokens are encrypted at rest and are never returned by the API. One
that will not decrypt reads as *absent*: every caller has to fail closed.

### Things that will bite

- **The connector needs both halves.** `mcp_servers` *and* a matching
  `mcp_toolset` in `tools`; one without the other is a validation error.
- **The connector is beta** (`mcp-client-2025-11-20`) and Claude API / Claude
  Platform on AWS only. It is one constant in `clients/connector.py`.
- **The local transport needs a round bound.** `MCP_CLIENT_MAX_TOOL_ROUNDS`,
  or a model that keeps asking for tools runs until the process is killed.
- **A stdio command comes from a `servers/` module, never the database.** A
  stored command would be remote code execution with extra steps.
- **`aask()`, not `arun()`, for async callers.** `arun` skips credential
  resolution and the audit record.

### The connections page

`/connections`, behind `VITE_MCP_CLIENT_ENABLED`. It lists what each server
would be able to do *before* anyone agrees to it — a connection screen that
does not name the tools is asking for consent to something unnamed — and a
server with no allow-list is called out rather than shown as an empty list.

Disconnecting deletes the token. Pausing (`enabled`) keeps it. Those are
different buttons on purpose.

---

## Dev tooling — `.mcp.json`

MCP servers for an assistant working on *this repository*: the compose
Postgres, read-only, and the filesystem. Optional, documented in
`CONTRIBUTING.md`, and safe to delete — nothing in the application reads it and
contributing does not require it.

Read-only Postgres is deliberate. An assistant that can read the schema answers
most questions; one that can write to a developer's database can lose an
afternoon of fixtures without meaning to.

---

## What has not been verified

Stated here rather than discovered later:

- **No full OAuth flow against a running authorization server.** No container
  runtime was available where this was built, so Ory Hydra was never started
  and discovery → authorize → login → consent → token → tool call was never
  driven end to end. The token validator is attacked by tests; the flow is not.
- **The auth revision MCP currently targets was not read.**
  `modelcontextprotocol.io` was unreachable from that environment. The
  implementation follows RFC 9728; confirm the revision before relying on it.
- **No real call to the Anthropic API.** The connector's request body,
  response handling, credential resolution and provider gate are covered
  against an injected SDK; no API key was available.
- **Dynamic client registration is not implemented and not decided.** MCP wants
  it so any client can connect unaided; an open registration endpoint is an
  abuse vector. Settle it before relying on unattended client onboarding, and
  rate-limit it if you enable it.

The local transport *is* verified end to end, against this application's own
MCP server: real handshake, real tool listing, real tool call reaching a real
Django view. That both halves live in one process turned out to be worth more
than the deployment simplicity it was chosen for.
