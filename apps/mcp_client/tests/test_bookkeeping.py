"""What a call leaves behind.

An outbound call reaches a service this application does not control, on
behalf of a user. That is exactly the kind of thing the audit log exists for,
so the record is part of the feature rather than a nicety.
"""

import pytest
from django.conf import settings

from apps.core.audit import AuditAction
from apps.mcp_client.clients.connector import ConnectorMCPClient
from apps.mcp_client.models import ConnectedServer
from apps.mcp_client.registry import ServerDefinition

from .fakes import FakeAnthropic, block_response, text_block, tool_use_block

pytestmark = pytest.mark.django_db

DEFINITION = ServerDefinition(
    slug='example', label='Example', url='https://mcp.example.com/mcp'
)


def _client(user=None, api=None):
    return ConnectorMCPClient(DEFINITION, user=user, api=api or FakeAnthropic())


@pytest.mark.skipif(not settings.AUDIT_LOG_ENABLED, reason='the audit log is off')
def test_a_call_is_recorded_with_the_tools_it_used(user):
    from apps.audit.models import AuditEvent

    api = FakeAnthropic(
        response=block_response(tool_use_block('u1', 'search', {'q': 'x'}), text_block('done'))
    )
    _client(user=user, api=api).ask('find it')

    event = AuditEvent.objects.filter(action=AuditAction.MCP_SERVER_CALLED).first()
    assert event is not None
    assert event.target == 'example'
    assert event.metadata['tools_used'] == ['search']
    assert event.metadata['transport'] == 'connector'


@pytest.mark.skipif(not settings.AUDIT_LOG_ENABLED, reason='the audit log is off')
def test_the_arguments_and_results_are_not_recorded(user):
    """An outbound tool call can carry anything -- a document, a customer
    record, a key someone pasted into a prompt. The audit log is deliberately
    hard to edit and kept for a long time, so it is the wrong place to find
    out what."""
    from apps.audit.models import AuditEvent

    api = FakeAnthropic(
        response=block_response(tool_use_block('u1', 'search', {'q': 'sensitive'}))
    )
    _client(user=user, api=api).ask('find it')

    stored = str(AuditEvent.objects.first().metadata)
    assert 'sensitive' not in stored


def test_a_call_with_the_audit_log_off_still_works(user):
    """audit() no-ops when the flag is off, and this must not be the thing
    that couples the two features."""
    api = FakeAnthropic()
    from django.test import override_settings

    with override_settings(AUDIT_LOG_ENABLED=False):
        result = _client(user=user, api=api).ask('hello')

    assert result.raw is not None


def test_using_a_connection_stamps_it(user):
    connection = ConnectedServer(user=user, slug='example')
    connection.set_credential('tok')
    connection.save()
    assert connection.last_used_at is None

    _client(user=user).ask('hello')

    connection.refresh_from_db()
    assert connection.last_used_at is not None


def test_stamping_does_not_clobber_a_concurrent_credential_write(user):
    """The stamp is a queryset update rather than a save(), so a credential
    written between loading the row and finishing the call survives."""
    connection = ConnectedServer(user=user, slug='example')
    connection.set_credential('old')
    connection.save()

    client = _client(user=user)
    stale = client.connection()  # loaded before the credential changes

    fresh = ConnectedServer.objects.get(pk=connection.pk)
    fresh.set_credential('new')
    fresh.save()

    client._record(client.ask('hello'))

    assert stale is not None
    connection.refresh_from_db()
    assert connection.credential == 'new'
