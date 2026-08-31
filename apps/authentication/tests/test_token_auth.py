"""The bearer-token flow the mobile client signs in with.

Two things are being pinned here. The obvious one is that the flow works:
credentials in, pair out, refresh rotates, revoke revokes.

The less obvious one is coexistence. Session auth, API keys, MCP OAuth and
this all sit in one DEFAULT_AUTHENTICATION_CLASSES list, and two of them read
the same `Authorization: Bearer` header. Getting that wrong does not fail
loudly -- it fails as "the mobile app cannot log in, but only in the
deployments that also turned MCP OAuth on".
"""

import jwt
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.authentication import token_services
from apps.authentication.authentication_token import MobileJWTAuthentication
from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def obtain(client, user, password=DEFAULT_PASSWORD):
    return client.post(
        reverse('v1:token_obtain'), {'identifier': user.email, 'password': password}
    )


def bearer(access):
    return APIClient(HTTP_AUTHORIZATION=f'Bearer {access}')


# ---------------------------------------------------------------------------
# Obtaining a pair
# ---------------------------------------------------------------------------


def test_valid_credentials_return_a_pair_and_the_user(api_client, user):
    response = obtain(api_client, user)

    assert response.status_code == 200
    data = response.data['data']
    assert data['access']
    assert data['refresh']
    assert data['access_expires_in'] > 0
    assert data['user']['username'] == user.username


def test_the_token_endpoint_needs_no_csrf_token(api_client, user):
    """`api_client` enforces CSRF. A header-authenticated client has no cookie
    to defend, and requiring one would make the mobile app fetch a CSRF token
    it can then never use."""
    assert obtain(api_client, user).status_code == 200


def test_a_wrong_password_issues_nothing(api_client, user):
    response = obtain(api_client, user, password='not-the-password')

    assert response.status_code == 400
    assert 'access' not in (response.data.get('data') or {})


def test_the_token_endpoint_does_not_reveal_whether_the_account_exists(api_client, user):
    missing = api_client.post(
        reverse('v1:token_obtain'), {'identifier': 'nobody', 'password': 'wrong'}
    )
    wrong_password = obtain(api_client, user, password='wrong')

    assert missing.status_code == wrong_password.status_code == 400
    assert missing.data['errors'] == wrong_password.data['errors']


def test_an_inactive_user_is_refused(api_client):
    inactive = UserFactory(is_active=False)

    assert obtain(api_client, inactive).status_code == 400


# ---------------------------------------------------------------------------
# Using one
# ---------------------------------------------------------------------------


def test_the_access_token_authenticates_an_ordinary_request(api_client, user):
    access = obtain(api_client, user).data['data']['access']

    response = bearer(access).get(reverse('v1:user_me'))

    assert response.status_code == 200
    assert response.data['data']['username'] == user.username


def test_a_garbled_token_is_refused_rather_than_ignored(api_client, user):
    obtain(api_client, user)

    response = bearer('not-a-jwt').get(reverse('v1:user_me'))

    assert response.status_code == 401


def test_no_credential_at_all_is_a_401_with_a_challenge(api_client):
    """401 rather than 403, which is what tells a client to authenticate.

    DRF builds this from `authenticators[0]`, which is MobileJWTAuthentication.
    A class there that offered no challenge would turn every anonymous request
    into a 403 across the whole API.
    """
    response = api_client.get(reverse('v1:user_me'))

    assert response.status_code == 401
    assert response.headers['WWW-Authenticate'].startswith('Bearer')


# ---------------------------------------------------------------------------
# Refresh and revoke
# ---------------------------------------------------------------------------


def test_refreshing_returns_a_new_pair(api_client, user):
    original = obtain(api_client, user).data['data']

    response = api_client.post(reverse('v1:token_refresh'), {'refresh': original['refresh']})

    assert response.status_code == 200
    assert response.data['data']['refresh'] != original['refresh']
    assert (
        bearer(response.data['data']['access']).get(reverse('v1:user_me')).status_code == 200
    )


def test_a_refresh_token_cannot_be_spent_twice(api_client, user):
    """Rotation with blacklisting. The second attempt failing is the only
    signal a server ever gets that a refresh token leaked."""
    refresh = obtain(api_client, user).data['data']['refresh']

    first = api_client.post(reverse('v1:token_refresh'), {'refresh': refresh})
    second = api_client.post(reverse('v1:token_refresh'), {'refresh': refresh})

    assert first.status_code == 200
    assert second.status_code == 401


def test_refresh_failure_is_401_so_the_client_knows_to_sign_in_again(api_client):
    response = api_client.post(reverse('v1:token_refresh'), {'refresh': 'nonsense'})

    assert response.status_code == 401


def test_revoking_stops_the_refresh_token_working(api_client, user):
    refresh = obtain(api_client, user).data['data']['refresh']

    revoked = api_client.post(reverse('v1:token_revoke'), {'refresh': refresh})
    reused = api_client.post(reverse('v1:token_refresh'), {'refresh': refresh})

    assert revoked.status_code == 200
    assert reused.status_code == 401


def test_revoking_twice_still_reports_success(api_client, user):
    """Logging out is not a thing worth failing. The caller asked for this
    token to stop working, and it does not work."""
    refresh = obtain(api_client, user).data['data']['refresh']
    api_client.post(reverse('v1:token_revoke'), {'refresh': refresh})

    assert api_client.post(reverse('v1:token_revoke'), {'refresh': refresh}).status_code == 200


# ---------------------------------------------------------------------------
# The second-factor branch
# ---------------------------------------------------------------------------


def test_the_challenge_is_not_redeemable_after_a_password_change(user):
    """A challenge outlives the password it was minted against otherwise.

    Someone reacting to a compromise by changing their password would leave
    an outstanding challenge good for its full window.
    """
    challenge = token_services.issue_challenge(user)
    assert token_services.user_for_challenge(challenge) == user

    user.set_password('a-completely-different-password')
    user.save(update_fields=['password'])

    assert token_services.user_for_challenge(challenge) is None


def test_a_forged_challenge_is_refused():
    assert token_services.user_for_challenge('made.up.value') is None


# ---------------------------------------------------------------------------
# Sharing the Authorization header
# ---------------------------------------------------------------------------


def test_the_mobile_authenticator_declines_a_token_that_is_not_ours():
    """The property that lets two bearer schemes coexist.

    MobileJWTAuthentication must *decline* a foreign token so the next
    authenticator gets it. If it raised instead -- which is what SimpleJWT's
    own class does -- it would reject every MCP OAuth token before
    apps.mcp_oauth ever ran, and it sits ahead of that class in the list.
    """
    # A syntactically valid JWT carrying somebody else's issuer.
    foreign = jwt.encode(
        {'iss': 'https://auth.example.com', 'sub': '1'},
        'a-key-from-somewhere-else-long-enough-for-hs256',
    )

    request = type('Req', (), {'META': {'HTTP_AUTHORIZATION': f'Bearer {foreign}'}})()

    assert MobileJWTAuthentication().authenticate(request) is None


def test_the_mobile_authenticator_ignores_a_request_with_no_bearer_header():
    request = type('Req', (), {'META': {}})()

    assert MobileJWTAuthentication().authenticate(request) is None


def test_session_auth_is_untouched(api_client, user):
    """The website's login still establishes a session.

    Adding a bearer class to the front of the list must not change what the
    browser does -- it is added to the authentication classes, never
    substituted for them.
    """
    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert '_auth_user_id' in api_client.session


# ---------------------------------------------------------------------------
# Keeping the blacklist from growing forever
# ---------------------------------------------------------------------------


def test_expired_blacklisted_tokens_are_swept_on_a_schedule():
    """Rotation writes a row per refresh and nothing else removes them.

    Roughly a hundred rows per device per day, forever. This was documented
    before it was scheduled, which is the worse of the two failures: a reader
    is told to handle it and given no mechanism.
    """
    from django.conf import settings

    entry = settings.CELERY_BEAT_SCHEDULE['flush-expired-tokens']

    assert entry['task'] == 'apps.authentication.tasks.flush_expired_tokens'


def test_the_sweep_only_deletes_tokens_that_have_already_expired(user):
    """So running it can never shorten a blacklisting.

    `flushexpiredtokens` is SimpleJWT's own command; this pins that the task
    calls it rather than deleting rows itself.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    from apps.authentication import token_services
    from apps.authentication.tasks import flush_expired_tokens

    pair = token_services.issue_pair(user)
    token_services.revoke(pair['refresh'])
    assert BlacklistedToken.objects.count() == 1

    flush_expired_tokens()

    # Still there: it is blacklisted but has not expired yet.
    assert BlacklistedToken.objects.count() == 1


def test_deleting_an_account_blacklists_its_outstanding_tokens(api_client, user):
    """A deleted account should leave no month-long credential outstanding.

    `is_active` is already false by then and SimpleJWT refuses an inactive
    user, so this is a second barrier rather than the only one -- but the
    session-backed client has its sessions dropped on deletion, and a token
    client would otherwise have nothing equivalent done for it.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    from utils.gdpr_utils import anonymize_user_data

    refresh = obtain(api_client, user).data['data']['refresh']
    assert BlacklistedToken.objects.count() == 0

    anonymize_user_data(user)

    assert BlacklistedToken.objects.count() == 1
    assert (
        api_client.post(reverse('v1:token_refresh'), {'refresh': refresh}).status_code == 401
    )
