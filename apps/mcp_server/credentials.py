"""The caller's credential, carried from the transport to the tool.

An MCP tool function receives its arguments and nothing else -- there is no
request object in its signature. The credential still has to reach it, because
every call this server makes is made *as the caller* and never as the server.

A context variable is the mechanism, set by the ASGI middleware in `asgi.py`
and read by `call_api`. Deliberately not an SDK internal: reaching into the
server's request context would couple every tool to a private API that moves
between releases, and this needs to keep working.

`ContextVar` rather than a module global because the server is async and
concurrent -- a global would let one caller's credential leak into another
caller's tool call, which is the worst bug this file could have.
"""

from __future__ import annotations

from contextvars import ContextVar

_credential: ContextVar[str | None] = ContextVar('mcp_credential', default=None)


class MissingCredential(Exception):
    """No usable credential on the request.

    Raised rather than falling back to anonymous: a tool that quietly runs
    unauthenticated would return an empty list where it should have refused,
    and an empty list reads like "you have none of those" rather than "I could
    not tell who you are".
    """


def set_credential(value: str | None):
    """Store the caller's Authorization header. Returns a reset token."""
    return _credential.set(value)


def reset_credential(token) -> None:
    _credential.reset(token)


def require_credential() -> str:
    """The caller's Authorization header, or refuse."""
    value = _credential.get()
    if not value:
        raise MissingCredential(
            'This tool needs an Authorization header. Send the credential you '
            'were issued -- the server has none of its own to fall back on.'
        )
    return value
