"""A key cannot manage keys.

If it could, a leaked read-only key buys a write key, and a stolen key mints
replacements that outlive revoking the original -- so revocation would stop
being a containment tool.
"""

import pytest
from django.urls import reverse

from apps.api_keys.models import APIKey
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def _auth(raw_key):
    return {'HTTP_AUTHORIZATION': f'Api-Key {raw_key}'}


def test_a_key_cannot_create_another_key(client, make_key):
    user = UserFactory()
    _key, raw_key = make_key(user=user, scope=APIKey.Scope.WRITE)

    response = client.post(
        reverse('v1:api_key_list'),
        {'name': 'escalated'},
        content_type='application/json',
        **_auth(raw_key),
    )

    assert response.status_code in (401, 403)
    assert APIKey.objects.filter(user=user).count() == 1


def test_a_key_cannot_list_keys(client, make_key):
    _key, raw_key = make_key(scope=APIKey.Scope.WRITE)

    response = client.get(reverse('v1:api_key_list'), **_auth(raw_key))

    assert response.status_code in (401, 403)


def test_a_key_cannot_revoke_a_key(client, make_key):
    user = UserFactory()
    key, raw_key = make_key(user=user, scope=APIKey.Scope.WRITE)
    victim, _raw = make_key(user=user)

    response = client.delete(reverse('v1:api_key_detail', args=[victim.pk]), **_auth(raw_key))

    assert response.status_code in (401, 403)
    victim.refresh_from_db()
    assert victim.revoked_at is None
    assert key.revoked_at is None


def test_the_management_views_accept_sessions_only():
    """Pinned directly, so the reason survives someone editing the view."""
    from rest_framework.authentication import SessionAuthentication

    from apps.api_keys.views import APIKeyDetailView, APIKeyListCreateView

    for view in (APIKeyListCreateView, APIKeyDetailView):
        assert view.authentication_classes == [SessionAuthentication]


def test_a_session_can_still_manage_keys(client):
    """The restriction is on the credential, not on the endpoint."""
    user = UserFactory()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.post(
        reverse('v1:api_key_list'), {'name': 'CI'}, content_type='application/json'
    )

    assert response.status_code == 201
