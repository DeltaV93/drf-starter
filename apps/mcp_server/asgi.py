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

import functools
import inspect
import logging

from django.conf import settings

from .credentials import reset_credential, set_credential
from .tools import all_tools

logger = logging.getLogger(__name__)


def _carrying_credential(tool):
    """Wrap a tool so it runs with the caller's credential in scope.

    The credential has to reach a tool that receives its arguments and nothing
    else, and it has to be set *in the task the tool actually runs in*.

    An ASGI middleware setting it during the HTTP request is the obvious
    design and it does not work. The Streamable HTTP transport hands the
    message to the MCP server loop, which runs in a task started by the
    application's lifespan -- so a context variable set in the request task is
    invisible by the time the tool runs, and every call refuses for want of a
    credential. The unit tests all passed, because they set the variable and
    called the tool function directly. It took a real client over the real
    transport to see it.

    So the credential comes from `context.headers`, which the SDK attaches to
    each message and which is therefore correct for the task doing the work.

    Nothing is validated here. This layer only carries the header; the
    application's own authentication decides whether it means anything, on
    every call. A check here would be a second place to get authorization
    wrong.
    """

    from mcp.server.mcpserver import Context

    signature = inspect.signature(tool)

    @functools.wraps(tool)
    async def wrapped(*args, context, **kwargs):
        headers = context.headers or {}
        # Header names are case-insensitive, and the mapping the transport
        # supplies may or may not be.
        header = next((v for k, v in headers.items() if k.lower() == 'authorization'), None)
        token = set_credential(header)
        try:
            return await tool(*args, **kwargs)
        finally:
            # In a finally: the context variable must not outlive the call
            # that set it, or a later caller inherits an earlier one's
            # identity.
            reset_credential(token)

    # The SDK builds a tool's JSON schema from its signature and leaves out
    # any parameter annotated `Context`. Both of these are needed for that:
    # __signature__ so the original arguments still appear, __annotations__
    # because the Context detection reads them, and dropping __wrapped__ so
    # inspect does not follow it back to a signature with no context at all.
    # Get this wrong and `context` becomes a *required* argument in the
    # published schema, which makes the tool uncallable by any client.
    wrapped.__signature__ = signature.replace(
        parameters=[
            *signature.parameters.values(),
            inspect.Parameter('context', inspect.Parameter.KEYWORD_ONLY, annotation=Context),
        ]
    )
    wrapped.__annotations__ = {
        **getattr(tool, '__annotations__', {}),
        'context': Context,
    }
    del wrapped.__wrapped__
    return wrapped


def _transport_security():
    """Which Host and Origin headers the endpoint will answer to.

    The SDK enables DNS-rebinding protection by default and defaults its
    allow-list to `127.0.0.1`, which is right for the case it was written for
    -- a local server a browser on the same machine could otherwise be tricked
    into addressing. It is wrong for a deployed application: behind a real
    domain every request arrives with `Host: app.example.com` and the endpoint
    answers **421 Misdirected Request**, having mounted perfectly.

    So the allow-list is derived from the two settings that already say where
    this deployment is served: ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS. There
    is nothing new to configure, and nothing that can drift from the Django
    side of the same question.

    Each host is listed twice, bare and with the SDK's `:*` port wildcard --
    `example.com` and `example.com:443` are the same deployment, and a client
    behind a proxy that keeps the port would otherwise be refused.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = list(getattr(settings, 'ALLOWED_HOSTS', []) or [])

    if '*' in hosts:
        # Django is already accepting any host, so there is no narrower answer
        # to give -- and an allow-list containing the literal '*' would match
        # nothing at all, which is worse than being explicit about it.
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=[],
            allowed_origins=[],
        )

    allowed_hosts = []
    for host in hosts:
        host = host.lstrip('.')  # ALLOWED_HOSTS uses a leading dot for subdomains
        if not host:
            continue
        allowed_hosts.extend([host, f'{host}:*'])

    origins = list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or [])
    frontend = getattr(settings, 'FRONTEND_URL', '')
    if frontend and frontend not in origins:
        origins.append(frontend)

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=origins,
    )


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
        server.add_tool(_carrying_credential(tool))

    logger.info('MCP server exposing %d tools', len(all_tools()))
    return server.streamable_http_app(
        # The SDK mounts at its own path inside this app; the outer router
        # has already decided the request belongs here, so the two have to
        # agree on what that path is.
        streamable_http_path=settings.MCP_MOUNT_PATH.rstrip('/') or '/',
        transport_security=_transport_security(),
    )
