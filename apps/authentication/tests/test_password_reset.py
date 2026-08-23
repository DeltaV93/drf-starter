import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

NEW_PASSWORD = 'a-brand-new-passphrase-42'


def _reset_credentials(user):
    return (
        urlsafe_base64_encode(force_bytes(user.pk)),
        default_token_generator.make_token(user),
    )


def test_request_sends_an_email_to_a_known_address(api_client, user):
    response = api_client.post(reverse('v1:password_reset_request'), {'email': user.email})

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_request_answers_the_same_for_an_unknown_address(api_client, user):
    known = api_client.post(reverse('v1:password_reset_request'), {'email': user.email})
    mail.outbox.clear()
    unknown = api_client.post(
        reverse('v1:password_reset_request'), {'email': 'nobody@example.com'}
    )

    assert known.status_code == unknown.status_code == 200
    assert known.data['message'] == unknown.data['message']
    assert mail.outbox == []


def test_request_rejects_a_malformed_address(api_client):
    response = api_client.post(reverse('v1:password_reset_request'), {'email': 'not-an-email'})

    assert response.status_code == 400
    assert 'email' in response.data['errors']


def test_validate_accepts_a_fresh_link(api_client, user):
    uid, token = _reset_credentials(user)

    response = api_client.get(
        reverse('v1:password_reset_validate', kwargs={'uidb64': uid, 'token': token})
    )

    assert response.status_code == 200
    assert response.data['data']['is_valid'] is True


def test_validate_rejects_a_bad_token(api_client, user):
    uid, _ = _reset_credentials(user)

    response = api_client.get(
        reverse('v1:password_reset_validate', kwargs={'uidb64': uid, 'token': 'nonsense'})
    )

    assert response.data['data']['is_valid'] is False


def test_validate_rejects_an_unparseable_uid(api_client):
    response = api_client.get(
        reverse('v1:password_reset_validate', kwargs={'uidb64': '@@@', 'token': 'nonsense'})
    )

    assert response.status_code == 200
    assert response.data['data']['is_valid'] is False


def test_confirm_sets_the_new_password(api_client, user):
    uid, token = _reset_credentials(user)

    response = api_client.post(
        reverse('v1:password_reset_confirm'),
        {
            'uid': uid,
            'token': token,
            'password': NEW_PASSWORD,
            'password_confirm': NEW_PASSWORD,
        },
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_a_reset_token_cannot_be_used_twice(api_client, user):
    uid, token = _reset_credentials(user)
    payload = {
        'uid': uid,
        'token': token,
        'password': NEW_PASSWORD,
        'password_confirm': NEW_PASSWORD,
    }
    api_client.post(reverse('v1:password_reset_confirm'), payload)

    second = api_client.post(reverse('v1:password_reset_confirm'), payload)

    assert second.status_code == 400


def test_confirm_rejects_mismatched_passwords(api_client, user):
    uid, token = _reset_credentials(user)

    response = api_client.post(
        reverse('v1:password_reset_confirm'),
        {
            'uid': uid,
            'token': token,
            'password': NEW_PASSWORD,
            'password_confirm': 'something-else-entirely',
        },
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(DEFAULT_PASSWORD)


def test_confirm_rejects_a_weak_password(api_client, user):
    uid, token = _reset_credentials(user)

    response = api_client.post(
        reverse('v1:password_reset_confirm'),
        {'uid': uid, 'token': token, 'password': 'abc', 'password_confirm': 'abc'},
    )

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_confirm_rejects_another_users_token(api_client, user):
    other = UserFactory()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(other)

    response = api_client.post(
        reverse('v1:password_reset_confirm'),
        {
            'uid': uid,
            'token': token,
            'password': NEW_PASSWORD,
            'password_confirm': NEW_PASSWORD,
        },
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(DEFAULT_PASSWORD)


def test_the_emailed_link_actually_works(api_client, user):
    api_client.post(reverse('v1:password_reset_request'), {'email': user.email})
    body = mail.outbox[0].body

    # The link the user receives must be one the confirm endpoint accepts.
    uid, token = body.split('/confirm-password/')[1].split()[0].rstrip('/').split('/')

    response = api_client.post(
        reverse('v1:password_reset_confirm'),
        {
            'uid': uid,
            'token': token,
            'password': NEW_PASSWORD,
            'password_confirm': NEW_PASSWORD,
        },
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
