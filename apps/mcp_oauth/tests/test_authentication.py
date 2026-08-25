"""What a bearer token can actually reach.

The validator is attacked in test_validation.py. This file is about the layer
above it: which Django account a verified token speaks for, and what that
account is then allowed to do.

Every test drives a real API endpoint through the full DRF stack rather than
calling the authentication class directly, because the question is not "does
this class return a user" but "does a request carrying this token get the
data". Only the JWKS fetch is replaced -- signature, audience, issuer, expiry
and algorithm pinning are all the real code.
"""

import pytest
from rest_framework.test import APIClient

from apps.mcp_oauth import validation
from apps.mcp_oauth.metadata import metadata_url

from .keys import LocalJWKS, mint, settings_ok

pytestmark = pytest.mark.django_db

ME = '/api/v1/users/me/'


@pytest.fixture(autouse=True)
def local_keys():
    """Publish the test key set instead of fetching one over the network.

    Installed on the module-level cache the validator already uses, so
    production's code path runs unchanged -- there is no test-only branch
    inside `validate`.
    """
    validation.reset_jwks_client()
    validation._jwks_client = LocalJWKS()
    yield
    validation.reset_jwks_client()


def _bearer(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


def test_a_valid_token_authenticates_as_its_subject(user):
    with settings_ok:
        response = _bearer(mint(sub=str(user.pk))).get(ME)

    assert response.status_code == 200
    assert response.data['data']['email'] == user.email


def test_a_token_for_an_unknown_subject_is_refused(user):
    """A token is never a reason to create an account.

    The authorization server delegates login to this application, so every
    legitimate subject already exists here. One that does not means the token
    came from somewhere it should not have.
    """
    with settings_ok:
        response = _bearer(mint(sub='999999')).get(ME)

    assert response.status_code == 401


def test_a_subject_that_is_not_a_valid_lookup_value_is_refused():
    """A non-numeric `sub` against a primary-key lookup.

    Django raises ValueError deep in the query rather than returning nothing,
    so without handling this the endpoint answers 500 -- which tells a prober
    that the value reached the database.
    """
    with settings_ok:
        response = _bearer(mint(sub='not-a-pk')).get(ME)

    assert response.status_code == 401


def test_a_token_for_a_deactivated_account_is_refused(user):
    user.is_active = False
    user.save(update_fields=['is_active'])

    with settings_ok:
        response = _bearer(mint(sub=str(user.pk))).get(ME)

    assert response.status_code == 401


def test_a_token_without_the_write_scope_may_read(user):
    """Guards the test below: the refusal must be about scope, not about the
    token being broken."""
    with settings_ok:
        response = _bearer(mint(sub=str(user.pk), scope='mcp:read')).get(ME)

    assert response.status_code == 200


def test_a_token_without_the_write_scope_may_not_write(user):
    with settings_ok:
        response = _bearer(mint(sub=str(user.pk), scope='mcp:read')).patch(
            ME, {'first_name': 'Should not stick'}, format='json'
        )

    assert response.status_code == 401
    user.refresh_from_db()
    assert user.first_name != 'Should not stick'


def test_a_token_with_the_write_scope_may_write(user):
    with settings_ok:
        response = _bearer(mint(sub=str(user.pk), scope='mcp:read mcp:write')).patch(
            ME, {'first_name': 'Ada'}, format='json'
        )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'Ada'


def test_an_expired_token_stops_working(user):
    """The same account, the same scope, one claim different."""
    import time

    now = int(time.time())
    with settings_ok:
        assert _bearer(mint(sub=str(user.pk))).get(ME).status_code == 200
        expired = mint(sub=str(user.pk), exp=now - 1, iat=now - 600)
        assert _bearer(expired).get(ME).status_code == 401


def test_a_refusal_does_not_say_why(user):
    """Distinguishing "expired" from "wrong audience" from "forged" turns the
    endpoint into an oracle for probing the configuration."""
    import time

    now = int(time.time())
    with settings_ok:
        reasons = [
            mint(sub=str(user.pk), exp=now - 1, iat=now - 600),
            mint(sub=str(user.pk), aud='https://elsewhere.test/'),
            mint(sub=str(user.pk), iss='https://attacker.example/'),
        ]
        # `detail` is DRF's own key: an authentication failure is raised
        # before any view runs, so it never reaches the api_response
        # envelope the endpoints themselves return.
        messages = {str(_bearer(t).get(ME).data['detail']) for t in reasons}

    assert len(messages) == 1


def test_no_credential_points_the_client_at_the_metadata_document():
    """RFC 9728 discovery, and the reason a fresh MCP client can connect with
    nothing configured but this endpoint's URL."""
    with settings_ok:
        response = APIClient().get(ME)

    assert response.status_code == 401
    challenge = response.headers['WWW-Authenticate']
    assert challenge.startswith('Bearer ')
    assert f'resource_metadata="{metadata_url()}"' in challenge


def test_session_authentication_still_works(auth_client):
    """The bearer class is appended to the defaults, not substituted for them.

    If it replaced them the SPA would stop working the moment OAuth was turned
    on, and that failure would show up in a browser rather than in CI.
    """
    assert auth_client.get(ME).status_code == 200


def test_a_malformed_authorization_header_falls_through_rather_than_erroring():
    """`Authorization: Basic ...` is not this scheme's business.

    Raising on it would break every other authentication class in the list.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Basic Zm9vOmJhcg==')

    with settings_ok:
        response = client.get(ME)

    # Refused for want of a credential, not with a 500.
    assert response.status_code == 401
