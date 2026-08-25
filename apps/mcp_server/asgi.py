"""The MCP endpoint, as an ASGI application.

Mounted by `template/asgi.py` at `/mcp`, beside Django rather than inside it.
Two consequences worth knowing:

- MCP traffic does not traverse Django's middleware. It does not need to --
  every tool reaches data through `call_api`, which makes a full in-process
  Django request that goes through all of it.
- The SPA catch-all cannot swallow `/mcp`, because the router dispatches before
  Django's URLconf is consulted.

The transport is the SDK's Streamable HTTP, which is ASGI-only -- its handler
is `handle_request(scope, receive, send)` with no WSGI entry point. That is the
reason the whole application moved to ASGI.
"""

from __future__ import annotations

import logging

from django.conf import settings

from .credentials import reset_credential, set_credential
from .tools import all_tools

logger = logging.getLogger(__name__)

AUTHORIZATION = b'authorization'


def _carry_credential(app):
    """ASGI middleware: lift the Authorization header into a context variable.

    A tool function receives its arguments and nothing else, so the credential
    has to travel out of band. Doing it here rather than reaching into the
    SDK's request context keeps every tool off a private API that moves between
    releases.

    Nothing is validated here. This layer only carries the header; the
    application's own authentication is what decides whether it means anything,
    on every single call. A check here would be a second place to get
    authorization wrong.
    """

    async def wrapped(scope, receive, send):
        if scope['type'] != 'http':
            await app(scope, receive, send)
            return

        header = None
        for key, value in scope.get('headers', []):
            if key.lower() == AUTHORIZATION:
                header = value.decode('latin-1')
                break

        # Reset in a finally: the context variable must not outlive the request
        # that set it, or a later caller inherits an earlier caller's identity.
        token = set_credential(header)
        try:
            await app(scope, receive, send)
        finally:
            reset_credential(token)

    return wrapped


def build_mcp_app():
    """Construct the MCP server and return its ASGI application."""
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(
        name=settings.MCP_SERVER_NAME,
        instructions=(
            'Tools for this application, acting as the user whose credential '
            'you send. Every call is scoped to that user: you can see and '
            'change only what they could. Start with whoami.'
        ),
    )

    for tool in all_tools():
        # The docstring becomes the tool description the model reads, and the
        # signature becomes the schema -- so both are load-bearing, not decor.
        server.add_tool(tool)

    logger.info('MCP server exposing %d tools', len(all_tools()))
    return _carry_credential(server.streamable_http_app())
