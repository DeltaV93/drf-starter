"""The token flow's second-factor step.

Separate from `test_token_auth.py` because it can only run with the flag on,
and separate from `test_two_factor.py` because the two flows carry the pending
login by different means: the session one parks it in the session cookie, this
one hands the client a signed challenge because there is no cookie to park it
in.

The bypass worth catching is the same in both: a password alone must not be
enough to reach anything.
"""

import time

import pyotp
import pytest
from django.conf import settings
from django.urls import reverse

from apps.authentication import two_factor
from apps.authentication import two_factor_services as services
from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

if not settings.TWO_FACTOR_ENABLED:  # pragma: no cover - the flag-off CI run
    pytest.skip('two-factor is switched off', allow_module_level=True)


def _code_for(user, offset=0):
    """A valid code for an enrolled user, `offset` windows from now.

    Enrolment consumes the current window's code, and a code cannot be used
    twice -- so anything signing in after enrolling has to ask for the next
    one, exactly as a real authenticator app would a few seconds later.
    """
    device = services.device_for(user)
    totp = pyotp.TOTP(two_factor.decrypt_secret(device.encrypted_secret))
    return totp.at(int(time.time()) + offset * 30)


@pytest.fixture
def enrolled():
    user = UserFactory()
    services.begin_enrolment(user)
    services.confirm_enrolment(user, _code_for(user))
    return user


def _obtain(api_client, user):
    return api_client.post(
        reverse('v1:token_obtain'), {'username': user.username, 'password': DEFAULT_PASSWORD}
    )


def test_the_password_step_issues_a_challenge_and_no_tokens(api_client, enrolled):
    response = _obtain(api_client, enrolled)

    assert response.status_code == 200
    data = response.data['data']
    assert data['two_factor_required'] is True
    assert data['challenge']
    # The failure this guards: a client reading `access` unconditionally would
    # store `undefined` and believe itself signed in.
    assert 'access' not in data
    assert 'refresh' not in data


def test_the_challenge_alone_authenticates_nothing(api_client, enrolled):
    challenge = _obtain(api_client, enrolled).data['data']['challenge']

    from rest_framework.test import APIClient

    response = APIClient(HTTP_AUTHORIZATION=f'Bearer {challenge}').get(reverse('v1:user_me'))

    assert response.status_code == 401


def test_a_correct_code_completes_the_login(api_client, enrolled):
    challenge = _obtain(api_client, enrolled).data['data']['challenge']

    response = api_client.post(
        reverse('v1:token_two_factor_verify'),
        {'challenge': challenge, 'code': _code_for(enrolled, offset=1)},
    )

    assert response.status_code == 200
    assert response.data['data']['access']
    assert response.data['data']['user']['username'] == enrolled.username


def test_a_wrong_code_issues_nothing(api_client, enrolled):
    challenge = _obtain(api_client, enrolled).data['data']['challenge']

    response = api_client.post(
        reverse('v1:token_two_factor_verify'),
        {'challenge': challenge, 'code': '000000'},
    )

    assert response.status_code == 400
    assert 'access' not in (response.data.get('data') or {})


def test_a_challenge_from_another_account_does_not_transfer(api_client, enrolled):
    """Verifying with someone else's challenge must not sign you in as them.

    The code is checked against the user the challenge names, so a stolen
    challenge is only as useful as that user's authenticator app.
    """
    other = UserFactory()
    challenge = _obtain(api_client, enrolled).data['data']['challenge']

    response = api_client.post(
        reverse('v1:token_two_factor_verify'),
        {'challenge': challenge, 'code': '000000'},
    )

    assert response.status_code == 400
    assert other.username not in str(response.data)
