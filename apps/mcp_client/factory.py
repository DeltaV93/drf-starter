"""Getting a client for a slug, without a caller knowing the transport.

A caller says which server it wants and who is asking. Whether that means
Anthropic fetching an HTTPS endpoint or this process launching a subprocess is
the server definition's business, and changing it is editing one line in one
`servers/` module -- no call site moves.
"""

from __future__ import annotations

from .clients.base import BaseMCPClient, MCPClientError
from .registry import ServerDefinition, get

# Populated lazily: importing a transport pulls in its dependencies, and a
# deployment using only the connector should not need the local transport's.
_TRANSPORTS: dict[str, str] = {
    'connector': 'apps.mcp_client.clients.connector.ConnectorMCPClient',
    'local': 'apps.mcp_client.clients.local.LocalMCPClient',
}


def client_for(slug: str, *, user=None, **kwargs) -> BaseMCPClient:
    """A ready client for one server.

    Raises UnknownServer for a slug this deployment has not enabled -- which
    is the same answer as "no such server", on purpose: a caller has no
    business distinguishing "not configured here" from "does not exist".
    """
    return client_for_definition(get(slug), user=user, **kwargs)


def client_for_definition(
    definition: ServerDefinition, *, user=None, **kwargs
) -> BaseMCPClient:
    from django.utils.module_loading import import_string

    path = _TRANSPORTS.get(definition.transport)
    if path is None:
        raise MCPClientError(
            f'{definition.slug} asks for transport {definition.transport!r}, '
            f'which does not exist. Available: {", ".join(sorted(_TRANSPORTS))}.'
        )

    try:
        client_class = import_string(path)
    except ImportError as exc:
        raise MCPClientError(
            f'The {definition.transport} transport could not be loaded: {exc}'
        ) from exc

    return client_class(definition, user=user, **kwargs)
