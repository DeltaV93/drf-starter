"""The admin's own forms.

Django's `UserAdmin` names `username` in its fieldsets and its add form, so
these break silently when the identifier moves to the email address: the
system checks pass, and creating a user is what fails.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.authentication.backends import PASSWORD_BACKEND
from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client_(client):
    staff = UserFactory(is_staff=True, is_superuser=True, username='root')
    client.force_login(staff, backend=PASSWORD_BACKEND)
    return client


def test_the_add_form_creates_a_user_from_an_address_alone(admin_client_):
    response = admin_client_.post(
        reverse('admin:users_customuser_add'),
        {
            'email': 'new@example.com',
            'password1': 'a-sufficiently-long-passphrase',
            'password2': 'a-sufficiently-long-passphrase',
            # Both carry a model default but no blank=True, so the admin's
            # form asks for them -- as it did before username became optional.
            'account_type': 'FREE',
            'role': 'USER',
        },
    )

    assert response.status_code == 302, getattr(response, 'context_data', None)
    user = User.objects.get(email='new@example.com')
    assert user.username is None
    assert user.check_password('a-sufficiently-long-passphrase')


def test_the_add_form_can_still_set_a_username(admin_client_):
    admin_client_.post(
        reverse('admin:users_customuser_add'),
        {
            'email': 'handle@example.com',
            'username': 'ada',
            'password1': 'a-sufficiently-long-passphrase',
            'password2': 'a-sufficiently-long-passphrase',
            'account_type': 'FREE',
            'role': 'USER',
        },
    )

    assert User.objects.get(email='handle@example.com').username == 'ada'


def test_the_change_form_loads(admin_client_):
    user = UserFactory()

    response = admin_client_.get(reverse('admin:users_customuser_change', args=[user.pk]))

    assert response.status_code == 200
