"""Two-factor: enrolment, the two-step login, and everything it must refuse.

The failures worth catching here are bypasses. A partial login that can reach
anything, a code that works twice, a recovery code that survives being spent --
each turns the second factor into decoration.
"""

import time

import pyotp
import pytest
from django.conf import settings
from django.urls import reverse

from apps.authentication import two_factor
from apps.authentication import two_factor_services as services
from apps.authentication.models import RecoveryCode, TwoFactorDevice
from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

if not settings.TWO_FACTOR_ENABLED:  # pragma: no cover - the flag-off CI run
    pytest.skip('two-factor is switched off', allow_module_level=True)


def _code_for(user, offset=0):
    """A currently-valid code for an enrolled user."""
    device = services.device_for(user)
    raw_secret = two_factor.decrypt_secret(device.encrypted_secret)
    totp = pyotp.TOTP(raw_secret)
    return totp.at(int(time.time()) + offset * 30)


@pytest.fixture
def enrolled():
    """A user with a confirmed device, plus their recovery codes."""
    user = UserFactory()
    services.begin_enrolment(user)
    codes = services.confirm_enrolment(user, _code_for(user))
    return user, codes


@pytest.fixture
def sign_in(client):
    def _sign_in(user):
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        return client

    return _sign_in


# --------------------------------------------------------------------------
# Enrolment
# --------------------------------------------------------------------------


def test_a_device_is_inactive_until_confirmed():
    """Enrolling without proving the codes work is how people lock themselves out."""
    user = UserFactory()

    services.begin_enrolment(user)

    assert not services.is_required_for(user)
    assert services.device_for(user).confirmed_at is None


def test_confirming_needs_a_correct_code():
    user = UserFactory()
    services.begin_enrolment(user)

    with pytest.raises(services.TwoFactorError):
        services.confirm_enrolment(user, '000000')

    assert not services.is_required_for(user)


def test_confirming_activates_and_issues_recovery_codes():
    user = UserFactory()
    services.begin_enrolment(user)

    codes = services.confirm_enrolment(user, _code_for(user))

    assert services.is_required_for(user)
    assert len(codes) == two_factor.RECOVERY_CODE_COUNT
    assert RecoveryCode.objects.filter(user=user).count() == len(codes)


def test_the_secret_is_encrypted_at_rest():
    """A database dump alone must not let someone generate codes forever."""
    user = UserFactory()
    uri = services.begin_enrolment(user)

    device = TwoFactorDevice.objects.get(user=user)
    raw_secret = two_factor.decrypt_secret(device.encrypted_secret)

    assert raw_secret
    assert raw_secret not in device.encrypted_secret
    assert raw_secret in uri  # the provisioning URI is the one place it appears


def test_a_secret_that_cannot_be_decrypted_fails_closed(enrolled, monkeypatch):
    """A key problem must never be mistaken for a valid code."""
    user, _codes = enrolled
    device = services.device_for(user)
    device.encrypted_secret = 'not-a-valid-fernet-token'
    device.save(update_fields=['encrypted_secret'])

    with pytest.raises(services.TwoFactorError):
        services.verify(user, '123456')


def test_recovery_codes_are_stored_hashed(enrolled):
    user, codes = enrolled

    stored = set(RecoveryCode.objects.filter(user=user).values_list('hashed_code', flat=True))

    for code in codes:
        assert code not in stored
        assert two_factor.hash_recovery_code(code) in stored


# --------------------------------------------------------------------------
# The two-step login
# --------------------------------------------------------------------------


def test_a_password_alone_does_not_establish_a_session(client, enrolled):
    """The whole point. request.user must stay anonymous."""
    user, _codes = enrolled

    response = client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert response.json()['data']['twoFactorRequired'] is True
    assert '_auth_user_id' not in client.session


def test_a_pending_login_cannot_reach_anything(client, enrolled):
    """A half-finished login must do nothing but be verified."""
    user, _codes = enrolled
    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert client.get(reverse('v1:user_me')).status_code in (401, 403)


def test_verifying_completes_the_login(client, enrolled):
    user, _codes = enrolled
    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    # Confirming enrolment consumed the current step, so this uses the next
    # one -- as a user would, a moment later.
    response = client.post(
        reverse('v1:two_factor_verify'),
        {'code': _code_for(user, offset=1)},
        content_type='application/json',
    )

    assert response.status_code == 200, response.content
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.get(reverse('v1:user_me')).status_code == 200


def test_verifying_without_a_pending_login_is_refused(client, enrolled):
    """Otherwise the endpoint is a way in with only a code."""
    user, _codes = enrolled

    response = client.post(
        reverse('v1:two_factor_verify'),
        {'code': _code_for(user)},
        content_type='application/json',
    )

    assert response.status_code == 400
    assert '_auth_user_id' not in client.session


def test_a_wrong_code_leaves_the_login_unfinished(client, enrolled):
    user, _codes = enrolled
    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    response = client.post(
        reverse('v1:two_factor_verify'), {'code': '000000'}, content_type='application/json'
    )

    assert response.status_code == 400
    assert '_auth_user_id' not in client.session


def test_a_pending_login_expires(client, enrolled, settings):
    """A password-verified state must not sit in a cookie indefinitely."""
    user, _codes = enrolled
    client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    settings.TWO_FACTOR_PENDING_TIMEOUT = -1

    response = client.post(
        reverse('v1:two_factor_verify'),
        {'code': _code_for(user)},
        content_type='application/json',
    )

    assert response.status_code == 400
    assert '_auth_user_id' not in client.session


def test_a_user_without_two_factor_logs_in_in_one_step(client):
    user = UserFactory()

    response = client.post(
        reverse('v1:login'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert 'twoFactorRequired' not in response.json()['data']
    assert client.session['_auth_user_id'] == str(user.pk)


# --------------------------------------------------------------------------
# Replay
# --------------------------------------------------------------------------


def test_the_same_code_cannot_be_used_twice(enrolled):
    """A code is valid for its whole window; one read over a shoulder must not
    still work a few seconds later."""
    user, _codes = enrolled
    code = _code_for(user, offset=1)
    services.verify(user, code)

    with pytest.raises(services.TwoFactorError, match='already been used'):
        services.verify(user, code)


def test_a_recovery_code_works_once(enrolled):
    user, codes = enrolled

    assert services.verify(user, codes[0]) == 'recovery'

    with pytest.raises(services.TwoFactorError):
        services.verify(user, codes[0])


def test_a_recovery_code_can_be_typed_as_displayed(enrolled):
    """Users paste them with the spacing they were shown in."""
    user, codes = enrolled
    spaced = f'{codes[0][:5]} {codes[0][5:]}'.upper()

    assert services.verify(user, spaced) == 'recovery'


def test_other_recovery_codes_survive_one_being_used(enrolled):
    user, codes = enrolled
    services.verify(user, codes[0])

    assert services.verify(user, codes[1]) == 'recovery'


def test_a_recovery_code_from_another_user_is_refused(enrolled):
    user, _codes = enrolled
    other = UserFactory()
    services.begin_enrolment(other)
    other_codes = services.confirm_enrolment(other, _code_for(other))

    with pytest.raises(services.TwoFactorError):
        services.verify(user, other_codes[0])


# --------------------------------------------------------------------------
# Re-authentication
# --------------------------------------------------------------------------


def test_enrolling_requires_the_current_password(client, sign_in):
    """A session left open on a shared machine must not be enough."""
    user = UserFactory()
    sign_in(user)

    response = client.post(
        reverse('v1:two_factor_enrol'),
        {'password': 'not-the-password'},
        content_type='application/json',
    )

    assert response.status_code == 400
    assert services.device_for(user) is None


def test_disabling_requires_the_current_password(client, sign_in, enrolled):
    user, _codes = enrolled
    sign_in(user)

    response = client.post(
        reverse('v1:two_factor_disable'),
        {'password': 'not-the-password'},
        content_type='application/json',
    )

    assert response.status_code == 400
    assert services.is_required_for(user)


def test_disabling_with_the_password_works(client, sign_in, enrolled):
    user, _codes = enrolled
    sign_in(user)

    response = client.post(
        reverse('v1:two_factor_disable'),
        {'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert not services.is_required_for(user)


def test_disabling_destroys_the_recovery_codes(client, sign_in, enrolled):
    """A stale code must not work against a later enrolment."""
    user, _codes = enrolled
    sign_in(user)

    client.post(
        reverse('v1:two_factor_disable'),
        {'password': DEFAULT_PASSWORD},
        content_type='application/json',
    )

    assert RecoveryCode.objects.filter(user=user).count() == 0


def test_regenerating_invalidates_the_previous_codes(enrolled):
    user, old_codes = enrolled

    new_codes = services.regenerate_recovery_codes(user)

    assert set(new_codes).isdisjoint(old_codes)
    with pytest.raises(services.TwoFactorError):
        services.verify(user, old_codes[0])


def test_a_confirmed_device_cannot_be_silently_replaced(enrolled):
    """Re-enrolling without disabling would swap the factor unnoticed."""
    user, _codes = enrolled

    with pytest.raises(services.TwoFactorError):
        services.begin_enrolment(user)
