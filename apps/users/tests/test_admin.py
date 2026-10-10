"""The admin's user pages, which Django's UserAdmin builds around a username.

Each of these renders a fieldset or form that would raise on a field the model
no longer has, so a page that loads at all is most of the assertion.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_the_user_list_loads_and_searches_by_email(admin_client):
    UserFactory(email='findme@example.com')

    response = admin_client.get(reverse('admin:users_customuser_changelist'), {'q': 'findme'})

    assert response.status_code == 200
    assert b'findme@example.com' in response.content


def test_the_change_page_loads(admin_client):
    user = UserFactory()

    response = admin_client.get(reverse('admin:users_customuser_change', args=[user.pk]))

    assert response.status_code == 200


def test_adding_a_user_asks_for_an_email_and_normalises_it(admin_client):
    url = reverse('admin:users_customuser_add')
    assert admin_client.get(url).status_code == 200

    response = admin_client.post(
        url,
        {
            'email': 'New.Person@Example.com',
            'usable_password': 'true',
            'password1': 'sufficiently-long-passphrase-9',
            'password2': 'sufficiently-long-passphrase-9',
            'account_type': User.AccountType.FREE,
            'role': User.Role.USER,
        },
    )

    assert response.status_code == 302, response.context['adminform'].form.errors
    user = User.objects.get(email='new.person@example.com')
    assert user.check_password('sufficiently-long-passphrase-9')


def test_adding_a_user_refuses_an_email_taken_in_another_case(admin_client):
    UserFactory(email='taken@example.com')

    response = admin_client.post(
        reverse('admin:users_customuser_add'),
        {
            'email': 'Taken@Example.com',
            'usable_password': 'true',
            'password1': 'sufficiently-long-passphrase-9',
            'password2': 'sufficiently-long-passphrase-9',
            'account_type': User.AccountType.FREE,
            'role': User.Role.USER,
        },
    )

    assert response.status_code == 200
    assert 'email' in response.context['adminform'].form.errors
    assert User.objects.filter(email__iexact='taken@example.com').count() == 1
