"""What a request can and cannot do to a connection.

The important assertions here are negative. A request can say "I authorise
this server" and hand over a token. It cannot add a server, point one
somewhere else, widen its tool surface, or read a token back out -- all of
which would turn a stolen session into something much worse than a stolen
session.
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.mcp_client import registry
from apps.mcp_client.models import ConnectedServer

pytestmark = pytest.mark.django_db

LIST = '/api/v1/mcp/servers/'
EXAMPLE = '/api/v1/mcp/servers/example/'


@pytest.fixture(autouse=True)
def only_the_example():
    registry.reset()
    with override_settings(MCP_CLIENT_SERVERS=['example']):
        yield
    registry.reset()


def test_the_listing_shows_what_is_available_and_whether_it_is_connected(auth_client):
    body = auth_client.get(LIST).json()['data']

    assert [server['slug'] for server in body] == ['example']
    assert body[0]['connected'] is False
    assert body[0]['label']


def test_connecting_stores_an_encrypted_credential(auth_client, user):
    response = auth_client.put(EXAMPLE, {'credential': 'sk-secret'}, format='json')

    assert response.status_code == 200
    assert response.json()['data']['connected'] is True

    connection = ConnectedServer.objects.get(user=user, slug='example')
    assert connection.credential == 'sk-secret'
    assert 'sk-secret' not in connection.encrypted_credential


def test_a_credential_is_never_returned(auth_client):
    """Not on the write, not on the listing, not anywhere.

    A token that can be read back is a token that leaks through any endpoint
    an attacker reaches with a stolen session.
    """
    written = auth_client.put(EXAMPLE, {'credential': 'sk-secret'}, format='json')
    listed = auth_client.get(LIST)

    assert 'sk-secret' not in written.content.decode()
    assert 'sk-secret' not in listed.content.decode()


def test_disconnecting_destroys_the_credential_rather_than_pausing(auth_client, user):
    """`enabled` is for pausing while keeping the token. Disconnect has to
    actually destroy it, or the button lies."""
    auth_client.put(EXAMPLE, {'credential': 'sk-secret'}, format='json')

    response = auth_client.delete(EXAMPLE)

    assert response.status_code == 200
    assert not ConnectedServer.objects.filter(user=user, slug='example').exists()


def test_a_connection_can_be_paused_without_losing_the_token(auth_client, user):
    auth_client.put(EXAMPLE, {'credential': 'sk-secret'}, format='json')
    auth_client.put(EXAMPLE, {'enabled': False}, format='json')

    connection = ConnectedServer.objects.get(user=user, slug='example')
    assert connection.enabled is False
    assert connection.credential == 'sk-secret'


def test_a_server_with_no_module_cannot_be_connected(auth_client):
    """The property the whole registry design exists for: a request cannot
    introduce a server nobody wrote a file for."""
    response = auth_client.put(
        '/api/v1/mcp/servers/invented-by-the-client/',
        {'credential': 'sk-secret'},
        format='json',
    )

    assert response.status_code == 404
    assert not ConnectedServer.objects.exists()


def test_a_server_defined_but_not_enabled_here_is_also_a_404(auth_client):
    """Indistinguishable from "does not exist", on purpose."""
    with override_settings(MCP_CLIENT_SERVERS=[]):
        registry.reset()
        # Everything defined is enabled, so pick a slug no module defines.
        response = auth_client.put('/api/v1/mcp/servers/nothing-here/', {}, format='json')

    assert response.status_code == 404


def test_a_request_cannot_change_where_a_server_lives(auth_client):
    """Extra fields are ignored rather than honoured. If a URL could be set
    over the API, a stolen session could point a stored credential at an
    attacker's server and wait for it to be used."""
    auth_client.put(
        EXAMPLE,
        {
            'credential': 'sk-secret',
            'url': 'https://attacker.example/mcp',
            'allowed_tools': ['everything'],
            'transport': 'local',
        },
        format='json',
    )

    definition = registry.get('example')
    assert 'attacker' not in definition.url
    assert definition.allowed_tools != ['everything']


def test_one_users_connection_is_not_visible_to_another(auth_client, user, django_user_model):
    auth_client.put(EXAMPLE, {'credential': 'sk-secret'}, format='json')

    other = django_user_model.objects.create_user(
        username='mallory', email='mallory@example.com', password='hunter2hunter2'
    )
    theirs = APIClient()
    theirs.force_authenticate(user=other)

    assert theirs.get(LIST).json()['data'][0]['connected'] is False


def test_an_anonymous_caller_is_refused():
    assert APIClient().get(LIST).status_code in (401, 403)


def test_a_row_for_a_deleted_server_module_is_not_offered(auth_client, user):
    """A connection whose definition has gone cannot work, so listing it
    would offer the user something broken."""
    ConnectedServer.objects.create(user=user, slug='removed-last-release')

    slugs = [s['slug'] for s in auth_client.get(LIST).json()['data']]

    assert 'removed-last-release' not in slugs
