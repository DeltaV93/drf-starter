import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'first_name': 'New',
        'last_name': 'User',
        'password': 'sufficiently-long-passphrase-9',
        'password2': 'sufficiently-long-passphrase-9',
    }
    payload.update(overrides)
    return payload


def test_register_creates_user_and_sends_verification_email(api_client):
    response = api_client.post(reverse('v1:register'), _payload())

    assert response.status_code == 201
    user = User.objects.get(username='newuser')
    assert user.check_password('sufficiently-long-passphrase-9')
    assert user.email_verified is False
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_register_returns_a_csrf_token_for_the_new_session(api_client):
    response = api_client.post(reverse('v1:register'), _payload())

    assert response.data['data']['csrfToken']


def test_register_rejects_mismatched_passwords(api_client):
    response = api_client.post(
        reverse('v1:register'), _payload(password2='something-else-entirely')
    )

    assert response.status_code == 400
    assert 'password2' in response.data['errors']
    assert not User.objects.filter(username='newuser').exists()


def test_register_rejects_a_weak_password(api_client):
    response = api_client.post(
        reverse('v1:register'), _payload(password='pass', password2='pass')
    )

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_register_rejects_a_password_similar_to_the_username(api_client):
    # Django's UserAttributeSimilarityValidator only fires when the serializer
    # passes the unsaved user through to validate_password.
    response = api_client.post(
        reverse('v1:register'),
        _payload(username='alexanderson', password='alexanderson', password2='alexanderson'),
    )

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_register_rejects_a_duplicate_email_regardless_of_case(api_client):
    UserFactory(email='taken@example.com')

    response = api_client.post(reverse('v1:register'), _payload(email='TAKEN@example.com'))

    assert response.status_code == 400
    assert 'email' in response.data['errors']


def test_register_rejects_a_duplicate_username(api_client):
    UserFactory(username='newuser')

    response = api_client.post(reverse('v1:register'), _payload())

    assert response.status_code == 400
    assert 'username' in response.data['errors']
