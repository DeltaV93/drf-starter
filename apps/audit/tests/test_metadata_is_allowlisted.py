"""What may be stored, and what must never be.

The audit table is deliberately hard to edit and deliberately kept for a long
time, which makes it the worst possible place for a secret to land. Metadata is
allow-listed per action so a careless call site cannot widen it.
"""

import pytest

from apps.core.audit import AuditAction, audit
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_allowed_keys_are_stored():
    event = audit(
        AuditAction.API_KEY_CREATED,
        actor=UserFactory(),
        target='CI key',
        prefix='abcd1234',
        scope='read',
    )

    assert event.metadata == {'prefix': 'abcd1234', 'scope': 'read'}


def test_an_unlisted_key_is_dropped():
    """Not an error -- auditing must never fail the thing it audits."""
    event = audit(
        AuditAction.API_KEY_CREATED,
        actor=UserFactory(),
        prefix='abcd1234',
        something_unexpected='value',
    )

    assert 'something_unexpected' not in event.metadata
    assert event.metadata == {'prefix': 'abcd1234'}


@pytest.mark.parametrize(
    'key',
    ['password', 'new_password', 'token', 'secret', 'api_key', 'card_number', 'cvv'],
)
def test_a_secret_is_never_stored_even_if_passed(key):
    event = audit(AuditAction.API_KEY_CREATED, actor=UserFactory(), **{key: 'hunter2'})

    assert key not in event.metadata
    assert 'hunter2' not in str(event.metadata)


def test_case_does_not_defeat_the_secret_filter():
    event = audit(AuditAction.API_KEY_CREATED, actor=UserFactory(), PASSWORD='hunter2')

    assert 'hunter2' not in str(event.metadata)


def test_an_action_with_no_allow_list_stores_no_metadata():
    """Adding an action without deciding what it may carry stores nothing."""
    event = audit(AuditAction.LOGOUT, actor=UserFactory(), anything='at all')

    assert event.metadata == {}


def test_recording_never_raises(monkeypatch):
    """A full log table must not turn a login into a 500."""
    from apps.audit import events

    def explode(*args, **kwargs):
        raise RuntimeError('database is on fire')

    monkeypatch.setattr(events.AuditEvent.objects, 'create', explode)

    assert audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory()) is None


def test_the_vocabulary_and_the_model_choices_stay_in_sync():
    """A constant added to one and not the other is a silently unusable action."""
    from apps.audit.models import Action

    assert set(Action.values) == set(AuditAction.all())
