import pytest
from django.db import IntegrityError

from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_email_is_unique():
    UserFactory(email='taken@example.com')

    with pytest.raises(IntegrityError):
        UserFactory(email='taken@example.com')


def test_display_name_prefers_the_full_name():
    user = UserFactory(first_name='Ada', last_name='Lovelace')

    assert user.get_display_name() == 'Ada Lovelace'


def test_display_name_falls_back_to_the_username():
    user = UserFactory(first_name='', last_name='', username='ada')

    assert user.get_display_name() == 'ada'


def test_new_users_are_not_flagged_as_anonymized():
    assert UserFactory().is_anonymized is False


def test_defaults_are_the_least_privileged():
    user = UserFactory()

    assert user.role == user.Role.USER
    assert user.account_type == user.AccountType.FREE
