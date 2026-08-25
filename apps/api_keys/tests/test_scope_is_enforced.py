"""A read-only key cannot write. Anywhere.

`HasWriteScope` shipped with API keys, is unit-tested, and was used by no view
at all -- so the `read` scope restricted nothing and the field was decorative.
The reason is worth keeping in mind: `permission_classes` on a view *replaces*
`DEFAULT_PERMISSION_CLASSES` rather than adding to them, so per-view opt-in
enforcement is enforcement that gets forgotten.

It is now refused during authentication, which every key-authenticated request
passes through and no view can override. These tests hit real endpoints rather
than calling the permission class directly, because calling the class directly
is exactly the test that passed while nothing used it.
"""

import pytest
from rest_framework.test import APIClient

from apps.api_keys.models import APIKey, generate_key

pytestmark = pytest.mark.django_db


def _client_with(user, scope):
    full_key, prefix, hashed_secret = generate_key()
    APIKey.objects.create(
        user=user,
        name=f'scope-{scope}',
        scope=scope,
        prefix=prefix,
        hashed_secret=hashed_secret,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Api-Key {full_key}')
    return client


def test_a_read_key_may_read(user):
    response = _client_with(user, APIKey.Scope.READ).get('/api/v1/users/me/')

    assert response.status_code == 200


def test_a_read_key_may_not_write(user):
    response = _client_with(user, APIKey.Scope.READ).patch(
        '/api/v1/users/me/', {'first_name': 'Should not stick'}, format='json'
    )

    assert response.status_code in {401, 403}
    user.refresh_from_db()
    assert user.first_name != 'Should not stick'


def test_a_write_key_may_write(user):
    """Guards the test above: the refusal is about scope, not about writes
    being broken for every key."""
    response = _client_with(user, APIKey.Scope.WRITE).patch(
        '/api/v1/users/me/', {'first_name': 'Ada'}, format='json'
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'Ada'


@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_every_unsafe_method_is_refused_to_a_read_key(user, method):
    client = _client_with(user, APIKey.Scope.READ)

    response = getattr(client, method)('/api/v1/users/me/')

    assert response.status_code in {401, 403}, (
        f'{method.upper()} was allowed to a read-only key with '
        f'{response.status_code}. Every unsafe method must be refused.'
    )
