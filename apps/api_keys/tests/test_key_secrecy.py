"""The secret exists once, in the response that created it.

If any of these fail, a key can be recovered by someone who should not have
it -- a staff member reading the admin, anyone with database access, or anyone
who can replay a listing response.
"""

import pytest
from django.urls import reverse

from apps.api_keys.models import APIKey, hash_secret, split_key
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def signed_in(client):
    def _sign_in(user=None):
        user = user or UserFactory()
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        return client, user

    return _sign_in


def _create(client, **payload):
    return client.post(
        reverse('v1:api_key_list'),
        {'name': 'CI', **payload},
        content_type='application/json',
    )


def test_creation_returns_the_key_once(signed_in):
    client, _user = signed_in()

    response = _create(client)

    assert response.status_code == 201, response.content
    data = response.json()['data']
    assert data['key']
    assert data['key'].startswith(data['prefix'] + '.')


def test_only_a_digest_of_the_secret_is_stored(signed_in):
    client, _user = signed_in()
    raw_key = _create(client).json()['data']['key']
    _prefix, secret = split_key(raw_key)

    key = APIKey.objects.get()

    assert key.hashed_secret == hash_secret(secret)
    assert secret not in key.hashed_secret
    # And the raw value appears nowhere on the row.
    row = APIKey.objects.filter(pk=key.pk).values().first()
    assert secret not in str(row)
    assert raw_key not in str(row)


def test_listing_never_returns_the_secret(signed_in):
    """The one place it existed was the creation response."""
    client, _user = signed_in()
    raw_key = _create(client).json()['data']['key']
    _prefix, secret = split_key(raw_key)

    response = client.get(reverse('v1:api_key_list'))

    body = response.content.decode()
    assert response.status_code == 200
    assert secret not in body
    assert raw_key not in body
    # The prefix is fine -- it is what makes a key identifiable in a log.
    assert APIKey.objects.get().prefix in body


def test_the_serializer_has_no_secret_field():
    """Belt and braces: a future field cannot leak it by accident."""
    from apps.api_keys.serializers import APIKeySerializer

    fields = set(APIKeySerializer().fields)
    assert 'hashed_secret' not in fields
    assert 'key' not in fields
    assert 'secret' not in fields


def test_you_cannot_see_or_revoke_someone_elses_key(signed_in, make_key):
    other_key, _raw = make_key()
    client, _user = signed_in()

    listing = client.get(reverse('v1:api_key_list'))
    assert listing.json()['data'] == []

    response = client.delete(reverse('v1:api_key_detail', args=[other_key.pk]))
    assert response.status_code == 404
    other_key.refresh_from_db()
    assert other_key.revoked_at is None
