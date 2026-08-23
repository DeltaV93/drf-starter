import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.factories import DEFAULT_PASSWORD

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_deletion_anonymizes_rather_than_removing_the_row(auth_client, user):
    response = auth_client.post(
        reverse('v1:account_deletion'),
        {'password': DEFAULT_PASSWORD, 'reason': 'No longer needed'},
    )

    assert response.status_code == 200

    user.refresh_from_db()
    assert User.objects.filter(pk=user.pk).exists()
    assert user.is_active is False
    assert user.date_deleted is not None
    assert user.username.startswith('deleted_user_')
    assert user.email.endswith('@deleted.invalid')
    assert user.first_name == 'Deleted'
    assert user.last_name == 'User'


def test_deletion_makes_the_password_unusable(auth_client, user):
    auth_client.post(reverse('v1:account_deletion'), {'password': DEFAULT_PASSWORD})

    user.refresh_from_db()
    assert user.has_usable_password() is False


def test_deletion_clears_the_phone_number(auth_client, user):
    user.phone_number = '+15555550123'
    user.save(update_fields=['phone_number'])

    auth_client.post(reverse('v1:account_deletion'), {'password': DEFAULT_PASSWORD})

    user.refresh_from_db()
    assert user.phone_number == ''


def test_deletion_requires_the_correct_password(auth_client, user):
    response = auth_client.post(
        reverse('v1:account_deletion'), {'password': 'not-the-password'}
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_active is True
    assert user.date_deleted is None


def test_deletion_requires_authentication(api_client):
    response = api_client.post(reverse('v1:account_deletion'), {'password': DEFAULT_PASSWORD})

    assert response.status_code in (401, 403)


def test_anonymizing_twice_is_a_no_op(auth_client, user):
    from utils.gdpr_utils import anonymize_user_data

    auth_client.post(reverse('v1:account_deletion'), {'password': DEFAULT_PASSWORD})
    user.refresh_from_db()
    first_username = user.username
    first_deleted_at = user.date_deleted

    anonymize_user_data(user)

    user.refresh_from_db()
    assert user.username == first_username
    assert user.date_deleted == first_deleted_at
