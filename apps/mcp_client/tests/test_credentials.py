"""Which credential a call uses, and when it refuses to make one.

The rule this file exists for: a server marked `requires_user_credential`
refuses rather than falling back to the deployment's token. Falling back would
let a user who has authorised nothing act with the deployment's authority --
the same confused-deputy shape the MCP *server* side avoids by holding no
credential of its own.
"""

import pytest

from apps.mcp_client.clients.base import MissingCredential
from apps.mcp_client.models import ConnectedServer
from apps.mcp_client.registry import ServerDefinition

from .fakes import FakeAnthropic

pytestmark = pytest.mark.django_db

SHARED = ServerDefinition(
    slug='shared',
    label='Shared',
    url='https://mcp.example.com/mcp',
    credential_env='TEST_MCP_TOKEN',
)

PERSONAL = ServerDefinition(
    slug='personal',
    label='Personal',
    url='https://mcp.example.com/mcp',
    credential_env='TEST_MCP_TOKEN',
    requires_user_credential=True,
)

PUBLIC = ServerDefinition(slug='public', label='Public', url='https://mcp.example.com/mcp')


def _client(definition, user=None):
    from apps.mcp_client.clients.connector import ConnectorMCPClient

    return ConnectorMCPClient(definition, user=user, api=FakeAnthropic())


def _connect(user, slug, credential='user-token', enabled=True):
    connection = ConnectedServer(user=user, slug=slug, enabled=enabled)
    connection.set_credential(credential)
    connection.save()
    return connection


def test_a_users_own_credential_wins_over_the_deployments(user, monkeypatch):
    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')
    _connect(user, 'shared')

    assert _client(SHARED, user=user).credential() == 'user-token'


def test_the_deployment_credential_is_the_fallback(user, monkeypatch):
    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')

    assert _client(SHARED, user=user).credential() == 'deployment-token'


def test_a_personal_server_refuses_rather_than_falling_back(user, monkeypatch):
    """The test this file exists for."""
    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')

    with pytest.raises(MissingCredential, match='Connect it first'):
        _client(PERSONAL, user=user).credential()


def test_a_personal_server_works_once_connected(user, monkeypatch):
    """Guards the test above: the refusal must be about the missing
    authorisation, not about personal servers being broken."""
    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')
    _connect(user, 'personal')

    assert _client(PERSONAL, user=user).credential() == 'user-token'


def test_a_disabled_connection_does_not_count_as_connected(user, monkeypatch):
    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')
    _connect(user, 'personal', enabled=False)

    with pytest.raises(MissingCredential):
        _client(PERSONAL, user=user).credential()


def test_a_public_server_needs_no_credential(user):
    """None is a legitimate answer: not every MCP server is authenticated."""
    assert _client(PUBLIC, user=user).credential() is None


def test_one_users_connection_is_not_anothers(user, django_user_model, monkeypatch):
    monkeypatch.delenv('TEST_MCP_TOKEN', raising=False)
    other = django_user_model.objects.create_user(
        username='mallory', email='mallory@example.com', password='hunter2hunter2'
    )
    _connect(user, 'shared', credential='alice-token')

    assert _client(SHARED, user=user).credential() == 'alice-token'
    assert _client(SHARED, user=other).credential() is None


def test_an_anonymous_caller_gets_no_stored_credential(user, monkeypatch):
    from django.contrib.auth.models import AnonymousUser

    monkeypatch.setenv('TEST_MCP_TOKEN', 'deployment-token')
    _connect(user, 'shared', credential='alice-token')

    assert _client(SHARED, user=AnonymousUser()).credential() == 'deployment-token'


# ---------------------------------------------------------------------------
# At rest.
# ---------------------------------------------------------------------------


def test_the_credential_is_not_stored_in_the_clear(user):
    """A database dump alone must not be a working credential for a
    third-party service."""
    connection = _connect(user, 'shared', credential='sk-very-secret')

    assert 'sk-very-secret' not in connection.encrypted_credential
    assert connection.credential == 'sk-very-secret'


def test_a_credential_that_will_not_decrypt_reads_as_absent(user):
    """Failing closed. A credential that cannot be read is the same as not
    having one -- never an exception a caller might treat as transient."""
    connection = _connect(user, 'shared')
    ConnectedServer.objects.filter(pk=connection.pk).update(
        encrypted_credential='not-a-valid-ciphertext'
    )
    connection.refresh_from_db()

    assert connection.credential is None


def test_a_user_has_at_most_one_connection_per_server(user):
    from django.db import IntegrityError

    _connect(user, 'shared')
    with pytest.raises(IntegrityError):
        _connect(user, 'shared')
