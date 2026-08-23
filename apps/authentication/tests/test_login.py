import pytest
from django.urls import reverse

from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_login_succeeds_with_valid_credentials(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert response.data['message'] == 'Login successful.'
    assert response.data['data']['user']['username'] == user.username
    assert '_auth_user_id' in api_client.session


def test_login_returns_the_rotated_csrf_token(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': DEFAULT_PASSWORD}
    )

    assert response.data['data']['csrfToken']


def test_login_rejects_a_wrong_password(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': 'not-the-password'}
    )

    assert response.status_code == 400
    assert '_auth_user_id' not in api_client.session


def test_login_does_not_reveal_whether_the_account_exists(api_client, user):
    missing = api_client.post(
        reverse('v1:login'), {'username': 'nobody', 'password': 'not-the-password'}
    )
    wrong_password = api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': 'not-the-password'}
    )

    assert missing.status_code == wrong_password.status_code == 400
    assert missing.data['errors'] == wrong_password.data['errors']


def test_login_rejects_an_inactive_user(api_client):
    user = UserFactory(is_active=False)

    response = api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 400


def test_login_requires_both_fields(api_client):
    response = api_client.post(reverse('v1:login'), {'username': 'someone'})

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_logout_clears_the_session(api_client, user):
    api_client.post(
        reverse('v1:login'), {'username': user.username, 'password': DEFAULT_PASSWORD}
    )
    csrf_token = api_client.cookies['csrftoken'].value

    response = api_client.post(reverse('v1:logout'), HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 200
    assert '_auth_user_id' not in api_client.session


def test_logout_requires_authentication(api_client):
    response = api_client.post(reverse('v1:logout'))

    assert response.status_code in (401, 403)
