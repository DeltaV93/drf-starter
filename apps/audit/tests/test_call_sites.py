"""The events that actually get recorded, exercised through the endpoints.

Written against the API rather than by calling audit() directly: a call site
that gets removed or never runs is the failure mode worth catching.
"""

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.core.audit import AuditAction
from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def _actions_for(user=None):
    events = AuditEvent.objects.all()
    if user is not None:
        events = events.filter(actor=user)
    return list(events.values_list('action', flat=True))


def test_a_successful_login_is_recorded(client):
    user = UserFactory()

    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert AuditAction.LOGIN_SUCCEEDED in _actions_for(user)


def test_a_failed_login_is_recorded_against_the_address_tried(client):
    """A run of failures against one account is the thing worth seeing."""
    user = UserFactory()

    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': 'wrong-password'},
        content_type='application/json',
    )

    event = AuditEvent.objects.get(action=AuditAction.LOGIN_FAILED)
    assert event.target == user.username
    assert event.actor is None  # Nobody authenticated.
    assert 'wrong-password' not in str(event.metadata)


def test_registration_is_recorded(client):
    response = client.post(
        reverse('v1:register'),
        {
            'username': 'audited',
            'email': 'audited@example.com',
            'first_name': 'A',
            'last_name': 'B',
            'password': 'sufficiently-long-passphrase-9',
            'password2': 'sufficiently-long-passphrase-9',
        },
        content_type='application/json',
    )

    assert response.status_code == 201, response.content
    assert AuditAction.ACCOUNT_CREATED in _actions_for()


def test_logout_is_recorded(client):
    user = UserFactory()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    client.post(reverse('v1:logout'))

    assert AuditAction.LOGOUT in _actions_for(user)


def test_a_password_reset_request_is_recorded(client):
    user = UserFactory()

    client.post(
        reverse('v1:password_reset_request'),
        {'email': user.email},
        content_type='application/json',
    )

    assert AuditAction.PASSWORD_RESET_REQUESTED in _actions_for(user)


def test_a_reset_request_for_an_unknown_address_records_nothing(client):
    """Recording it would make the log an account-enumeration oracle."""
    client.post(
        reverse('v1:password_reset_request'),
        {'email': 'nobody@example.com'},
        content_type='application/json',
    )

    assert AuditAction.PASSWORD_RESET_REQUESTED not in _actions_for()


def test_the_password_is_never_in_the_log(client):
    user = UserFactory()

    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    for event in AuditEvent.objects.all():
        assert DEFAULT_PASSWORD not in str(event.metadata)
        assert DEFAULT_PASSWORD not in event.target


# --------------------------------------------------------------------------
# Reading it back
# --------------------------------------------------------------------------


def test_you_can_read_your_own_activity(signed_in):
    client, user = signed_in()
    client.post(reverse('v1:logout'))
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.get(reverse('v1:audit_my_activity'))

    assert response.status_code == 200
    actions = {row['action'] for row in response.json()['data']['results']}
    assert AuditAction.LOGOUT in actions


def test_you_cannot_read_anyone_elses(signed_in):
    other = UserFactory()
    AuditEvent.objects.create(
        action=AuditAction.LOGIN_SUCCEEDED, actor=other, actor_label=other.email
    )

    client, _user = signed_in()
    response = client.get(reverse('v1:audit_my_activity'))

    labels = {row['actor_label'] for row in response.json()['data']['results']}
    assert other.email not in labels


def test_anonymous_callers_cannot_read_activity(client):
    response = client.get(reverse('v1:audit_my_activity'))

    assert response.status_code in (401, 403)
