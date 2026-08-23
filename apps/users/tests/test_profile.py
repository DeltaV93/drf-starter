import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_me_returns_the_current_user(auth_client, user):
    response = auth_client.get(reverse('v1:user_me'))

    assert response.status_code == 200
    data = response.data['data']
    assert data['username'] == user.username
    assert data['email'] == user.email


def test_me_never_exposes_the_password_hash(auth_client):
    response = auth_client.get(reverse('v1:user_me'))

    assert 'password' not in response.data['data']


def test_me_requires_authentication(api_client):
    response = api_client.get(reverse('v1:user_me'))

    assert response.status_code in (401, 403)


def test_patch_updates_editable_fields(auth_client, user):
    response = auth_client.patch(
        reverse('v1:user_me'),
        {'first_name': 'Ada', 'last_name': 'Lovelace', 'phone_number': '+15555550123'},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'Ada'
    assert user.last_name == 'Lovelace'
    assert user.phone_number == '+15555550123'


def test_patch_ignores_privilege_fields(auth_client, user):
    original_role = user.role

    response = auth_client.patch(
        reverse('v1:user_me'),
        {'first_name': 'Ada', 'role': 'ADMIN', 'account_type': 'PRO', 'email_verified': True},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.role == original_role
    assert user.account_type == user.AccountType.FREE


def test_patch_cannot_change_the_email_address(auth_client, user):
    original_email = user.email

    auth_client.patch(reverse('v1:user_me'), {'email': 'attacker@example.com'})

    user.refresh_from_db()
    assert user.email == original_email


def test_patch_returns_the_full_user_representation(auth_client):
    response = auth_client.patch(reverse('v1:user_me'), {'first_name': 'Ada'})

    assert response.data['data']['display_name'].startswith('Ada')
