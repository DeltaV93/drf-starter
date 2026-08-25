"""Opening a connection to an MCP server from this process.

An MCP `Transport` is just an async context manager yielding a read and a
write stream, which is why these are ten lines each rather than classes with
behaviour. They exist because the SDK's ready-made transports do not take
headers, and an authenticated HTTP server needs one.

Only `local.py` uses these. The connector transport never opens a connection
at all -- Anthropic does.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator


@contextlib.asynccontextmanager
async def http_transport(
    url: str, *, credential: str | None = None, timeout: float = 60.0
) -> AsyncGenerator[tuple, None]:
    """Streamable HTTP, carrying an Authorization header when there is one.

    The SDK's `StreamableHTTPTransport` takes a URL and nothing else, so the
    credential goes on a pre-built HTTP client, which is the documented way to
    configure headers for this transport.
    """
    import httpx2
    from mcp.client.streamable_http import streamable_http_client

    headers = {}
    if credential:
        headers['Authorization'] = _as_bearer(credential)

    async with httpx2.AsyncClient(headers=headers, timeout=timeout) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            yield streams


@contextlib.asynccontextmanager
async def stdio_transport(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> AsyncGenerator[tuple, None]:
    """A subprocess speaking MCP over its stdin and stdout.

    **The command comes from a `servers/` module, never from the database.**
    That is the whole safety argument: a row can say which server a user
    authorised, but what gets executed is in the repository and went through
    review. A stored command would be remote code execution with extra steps.

    `env` is passed as given rather than merged with this process's
    environment -- a subprocess should not inherit the application's database
    password and secret key because nobody thought about it.
    """
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    parameters = StdioServerParameters(
        command=command, args=list(args or []), env=dict(env or {}), cwd=cwd
    )
    async with stdio_client(parameters) as streams:
        yield streams


def _as_bearer(credential: str) -> str:
    """Let a definition supply either a bare token or a full scheme.

    `Bearer abc` and `abc` both mean the same thing here, and getting it wrong
    produces a 401 that says nothing about which of the two was expected.
    """
    if ' ' in credential.strip():
        return credential.strip()
    return f'Bearer {credential.strip()}'


# A transport yields streams; a `ClientSession` is what has `list_tools` and
# `call_tool` on it. The two are always entered together, so they are opened
# together here rather than at every call site.


@contextlib.asynccontextmanager
async def http_session(url: str, *, credential: str | None = None, timeout: float = 60.0):
    from mcp import ClientSession

    async with http_transport(url, credential=credential, timeout=timeout) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            yield session


@contextlib.asynccontextmanager
async def stdio_session(command: str, *, args=None, env=None, cwd=None):
    from mcp import ClientSession

    async with stdio_transport(command, args=args, env=env, cwd=cwd) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            yield session
