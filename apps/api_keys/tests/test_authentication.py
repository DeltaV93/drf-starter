"""Authenticating with a key, and the many ways it must fail."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.api_keys.models import APIKey
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

ME = 'v1:user_me'


def _auth(raw_key):
    return {'HTTP_AUTHORIZATION': f'Api-Key {raw_key}'}


def test_a_valid_key_authenticates(client, make_key):
    user = UserFactory()
    _key, raw_key = make_key(user=user)

    response = client.get(reverse(ME), **_auth(raw_key))

    assert response.status_code == 200
    assert response.json()['data']['email'] == user.email


def test_no_credential_is_still_refused(client):
    response = client.get(reverse(ME))

    assert response.status_code in (401, 403)


@pytest.mark.parametrize(
    'bad_key',
    [
        'nonsense',
        'no-dot-separator',
        'too.many.dots',
        '.missing-prefix',
        'missing-secret.',
        '',
    ],
)
def test_a_malformed_key_is_refused(client, bad_key):
    response = client.get(reverse(ME), **_auth(bad_key))

    assert response.status_code in (401, 403)


def test_a_wrong_secret_with_a_real_prefix_is_refused(client, make_key):
    key, _raw = make_key()

    response = client.get(reverse(ME), **_auth(f'{key.prefix}.wrong-secret'))

    assert response.status_code in (401, 403)


def test_a_revoked_key_stops_working(client, make_key):
    key, raw_key = make_key()
    assert client.get(reverse(ME), **_auth(raw_key)).status_code == 200

    key.revoke()

    assert client.get(reverse(ME), **_auth(raw_key)).status_code in (401, 403)


def test_an_expired_key_stops_working(client, make_key):
    key, raw_key = make_key(expires_at=timezone.now() + timedelta(hours=1))
    assert client.get(reverse(ME), **_auth(raw_key)).status_code == 200

    key.expires_at = timezone.now() - timedelta(seconds=1)
    key.save(update_fields=['expires_at'])

    assert client.get(reverse(ME), **_auth(raw_key)).status_code in (401, 403)


def test_a_key_belonging_to_a_deactivated_user_stops_working(client, make_key):
    user = UserFactory()
    _key, raw_key = make_key(user=user)

    user.is_active = False
    user.save(update_fields=['is_active'])

    assert client.get(reverse(ME), **_auth(raw_key)).status_code in (401, 403)


def test_every_failure_says_the_same_thing(client, make_key):
    """Otherwise a valid prefix can be identified by the wording."""
    key, _raw = make_key()
    key_revoked, revoked_raw = make_key()
    key_revoked.revoke()

    messages = {
        client.get(reverse(ME), **_auth('deadbeef.nope')).content,
        client.get(reverse(ME), **_auth(f'{key.prefix}.wrong')).content,
        client.get(reverse(ME), **_auth(revoked_raw)).content,
    }

    assert len(messages) == 1


def test_using_a_key_records_when(client, make_key):
    key, raw_key = make_key()
    assert key.last_used_at is None

    client.get(reverse(ME), **_auth(raw_key))

    key.refresh_from_db()
    assert key.last_used_at is not None


def test_last_used_is_not_rewritten_on_every_request(client, make_key):
    """It is a convenience, not an audit trail; a write per request is a cost."""
    key, raw_key = make_key()
    client.get(reverse(ME), **_auth(raw_key))
    key.refresh_from_db()
    first = key.last_used_at

    client.get(reverse(ME), **_auth(raw_key))

    key.refresh_from_db()
    assert key.last_used_at == first


# --------------------------------------------------------------------------
# Scope
# --------------------------------------------------------------------------


def test_a_read_key_may_read(client, make_key):
    _key, raw_key = make_key(scope=APIKey.Scope.READ)

    assert client.get(reverse(ME), **_auth(raw_key)).status_code == 200


def test_a_read_key_is_refused_an_unsafe_method(client, make_key):
    from apps.api_keys.permissions import HasWriteScope
    from apps.users.views import MeView

    # The permission is opt-in per view; assert its behaviour directly rather
    # than depending on which views happen to have adopted it.
    key, _raw = make_key(scope=APIKey.Scope.READ)

    class Request:
        method = 'PATCH'
        auth = key

    assert HasWriteScope().has_permission(Request(), MeView()) is False


def test_a_write_key_may_use_an_unsafe_method(client, make_key):
    from apps.api_keys.permissions import HasWriteScope
    from apps.users.views import MeView

    key, _raw = make_key(scope=APIKey.Scope.WRITE)

    class Request:
        method = 'PATCH'
        auth = key

    assert HasWriteScope().has_permission(Request(), MeView()) is True


def test_a_session_request_is_unaffected_by_scope(client):
    """The permission is about not upgrading a read key, not about sessions."""
    from apps.api_keys.permissions import HasWriteScope
    from apps.users.views import MeView

    class Request:
        method = 'PATCH'
        auth = None

    assert HasWriteScope().has_permission(Request(), MeView()) is True
