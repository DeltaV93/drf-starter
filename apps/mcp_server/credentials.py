"""The caller's credential, carried from the transport to the tool.

An MCP tool function receives its arguments and nothing else -- there is no
request object in its signature. The credential still has to reach it, because
every call this server makes is made *as the caller* and never as the server.

A context variable is the mechanism. It is set per tool call by the wrapper
in `asgi.py`, from the headers the SDK attaches to that message, and read by
`call_api`.

**Not from ASGI middleware, and that was a real bug rather than a preference.**
Setting it while handling the HTTP request looks equivalent and is not: the
Streamable HTTP transport hands the message to the MCP server loop, which runs
in a task started by the application's *lifespan*. A context variable set in
the request task is invisible there, so every tool refused every call for want
of a credential -- while the unit tests, which set the variable and called the
tool function directly, all passed. Nothing but a real client over the real
transport could have shown it.

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
