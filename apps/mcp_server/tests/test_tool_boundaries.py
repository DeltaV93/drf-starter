"""What a tool can and cannot reach.

These are the tests that matter. Everything else about MCP is plumbing; this
file is the part that decides whether handing an agent a credential is safe.

They exercise the real path — `call_api` makes a genuine in-process request
through Django's whole stack — so a permission class, throttle or scoping
filter that stopped being applied would show up here rather than in production.
"""

import pytest
from asgiref.sync import async_to_sync

from apps.api_keys.models import APIKey, generate_key
from apps.mcp_server.call import ApiError, call_api
from apps.mcp_server.credentials import (
    MissingCredential,
    require_credential,
    reset_credential,
    set_credential,
)
from apps.mcp_server.tools import identity, organizations

pytestmark = pytest.mark.django_db


def _key_for(user, scope=APIKey.Scope.READ):
    """Mint a usable key and return the header value a caller would send."""
    full_key, prefix, hashed_secret = generate_key()
    APIKey.objects.create(
        user=user,
        name=f'mcp-test-{scope}',
        scope=scope,
        prefix=prefix,
        hashed_secret=hashed_secret,
    )
    return f'Api-Key {full_key}'


class _As:
    """Run a block as the holder of a credential, then put it back."""

    def __init__(self, credential):
        self.credential = credential

    def __enter__(self):
        self.token = set_credential(self.credential)
        return self

    def __exit__(self, *exc):
        reset_credential(self.token)


def test_a_tool_returns_the_callers_own_profile(user):
    with _As(_key_for(user)):
        data = async_to_sync(identity.whoami)()

    assert data['username'] == user.username
    assert data['email'] == user.email


def test_a_tool_cannot_see_another_users_data(user, django_user_model):
    """The property everything else rests on.

    Two users, one credential. The tool must describe the credential's owner,
    never the other account -- and there is no argument a caller could pass to
    change that, because the endpoint scopes by the authenticated user.
    """
    other = django_user_model.objects.create_user(
        username='mallory', email='mallory@example.com', password='hunter2hunter2'
    )

    with _As(_key_for(other)):
        data = async_to_sync(identity.whoami)()

    assert data['username'] == other.username
    assert data['email'] != user.email


def test_a_read_scoped_credential_is_refused_a_write(user):
    """Scope is enforced by the API, not re-implemented in the tool."""
    with _As(_key_for(user, APIKey.Scope.READ)):
        with pytest.raises(ApiError) as caught:
            async_to_sync(call_api)(
                'PATCH',
                '/api/v1/users/me/',
                credential=require_credential(),
                body={'first_name': 'Should not stick'},
            )

    assert caught.value.status in {401, 403}
    user.refresh_from_db()
    assert user.first_name != 'Should not stick'


def test_a_write_scoped_credential_is_allowed_a_write(user):
    """Guards the test above: the refusal must be about scope, not about
    writes being broken for everyone."""
    from apps.mcp_server.tools import records

    with _As(_key_for(user, APIKey.Scope.WRITE)):
        async_to_sync(records.update_my_profile)(first_name='Ada')

    user.refresh_from_db()
    assert user.first_name == 'Ada'


def test_a_revoked_credential_stops_working(user):
    credential = _key_for(user)
    with _As(credential):
        async_to_sync(identity.whoami)()  # works before revoking

    APIKey.objects.filter(user=user).first().revoke()

    with _As(credential):
        with pytest.raises(ApiError) as caught:
            async_to_sync(identity.whoami)()

    # 403, not 401: SessionAuthentication is first in the default list and
    # offers no WWW-Authenticate header, so DRF has nothing to challenge with.
    assert caught.value.status in {401, 403}


def test_a_garbage_credential_is_refused(user):
    with _As('Api-Key not.arealkey'):
        with pytest.raises(ApiError) as caught:
            async_to_sync(identity.whoami)()

    assert caught.value.status in {401, 403}


def test_no_credential_refuses_rather_than_running_anonymously():
    """An anonymous fall-through would return an empty list, which reads as
    'you have none of those' rather than 'I could not tell who you are'."""
    with pytest.raises(MissingCredential):
        async_to_sync(organizations.list_organizations)()


def test_the_server_holds_no_credential_of_its_own(user):
    """There is no ambient identity to fall back on.

    If the MCP server had its own service credential, a tool could act with
    more authority than whoever called it -- the classic confused deputy.
    """
    with _As(None):
        with pytest.raises(MissingCredential):
            async_to_sync(identity.whoami)()
