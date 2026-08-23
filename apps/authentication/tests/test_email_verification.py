import pytest
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.authentication.tokens import email_verification_token_generator
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def unverified_user():
    return UserFactory(email_verified=False)


def _credentials(user):
    return (
        urlsafe_base64_encode(force_bytes(user.pk)),
        email_verification_token_generator.make_token(user),
    )


def test_verification_marks_the_address_confirmed(api_client, unverified_user):
    uid, token = _credentials(unverified_user)

    response = api_client.post(reverse('v1:verify_email'), {'uid': uid, 'token': token})

    assert response.status_code == 200
    unverified_user.refresh_from_db()
    assert unverified_user.email_verified is True


def test_a_verification_token_stops_working_once_used(api_client, unverified_user):
    uid, token = _credentials(unverified_user)
    api_client.post(reverse('v1:verify_email'), {'uid': uid, 'token': token})

    second = api_client.post(reverse('v1:verify_email'), {'uid': uid, 'token': token})

    assert second.status_code == 400


def test_verification_rejects_a_bad_token(api_client, unverified_user):
    uid, _ = _credentials(unverified_user)

    response = api_client.post(reverse('v1:verify_email'), {'uid': uid, 'token': 'nonsense'})

    assert response.status_code == 400
    unverified_user.refresh_from_db()
    assert unverified_user.email_verified is False


def test_a_password_reset_token_is_not_a_verification_token(api_client, unverified_user):
    from django.contrib.auth.tokens import default_token_generator

    uid = urlsafe_base64_encode(force_bytes(unverified_user.pk))
    token = default_token_generator.make_token(unverified_user)

    response = api_client.post(reverse('v1:verify_email'), {'uid': uid, 'token': token})

    assert response.status_code == 400


def test_resend_sends_to_an_unverified_address(api_client, unverified_user):
    response = api_client.post(
        reverse('v1:resend_verification'), {'email': unverified_user.email}
    )

    assert response.status_code == 200
    assert len(mail.outbox) == 1


def test_resend_is_silent_for_an_already_verified_address(api_client, user):
    response = api_client.post(reverse('v1:resend_verification'), {'email': user.email})

    assert response.status_code == 200
    assert mail.outbox == []


def test_resend_answers_the_same_for_an_unknown_address(api_client, unverified_user):
    known = api_client.post(
        reverse('v1:resend_verification'), {'email': unverified_user.email}
    )
    unknown = api_client.post(
        reverse('v1:resend_verification'), {'email': 'nobody@example.com'}
    )

    assert known.data['message'] == unknown.data['message']
