"""Getting a client without knowing the transport.

The point of the factory is that changing how a server is reached is editing
one line in one `servers/` module, and no call site moves. These tests are
what make that true rather than merely intended.
"""

import pytest
from django.test import override_settings

from apps.mcp_client import client_for, registry
from apps.mcp_client.clients.base import MCPClientError
from apps.mcp_client.factory import client_for_definition
from apps.mcp_client.registry import ServerDefinition, UnknownServer


@pytest.fixture(autouse=True)
def clear_registry():
    registry.reset()
    yield
    registry.reset()


def test_a_slug_resolves_to_a_transport():
    with override_settings(MCP_CLIENT_SERVERS=['example']):
        client = client_for('example')

    assert client.transport == 'connector'
    assert client.definition.slug == 'example'


def test_the_same_call_site_follows_a_changed_transport():
    """The property the factory exists for: only the definition changes."""
    connector = client_for_definition(
        ServerDefinition(slug='s', label='S', url='https://x.test/mcp')
    )
    local = client_for_definition(
        ServerDefinition(slug='s', label='S', transport='local', url='https://x.test/mcp')
    )

    # One line different in the definition, two different transports, and the
    # call site -- this function -- did not change.
    assert connector.transport == 'connector'
    assert local.transport == 'local'
    assert connector.definition.slug == local.definition.slug


def test_an_unknown_transport_names_the_ones_that_exist():
    with pytest.raises(MCPClientError, match='connector'):
        client_for_definition(
            ServerDefinition(slug='s', label='S', transport='carrier-pigeon')
        )


def test_an_unenabled_slug_is_refused():
    with override_settings(MCP_CLIENT_SERVERS=['example']):
        with pytest.raises(UnknownServer):
            client_for('not-enabled')
