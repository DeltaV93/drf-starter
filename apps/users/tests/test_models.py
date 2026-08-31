import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.users.factories import UserFactory

User = get_user_model()

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


def test_display_name_falls_back_to_the_email_when_there_is_no_username():
    user = UserFactory(first_name='', last_name='', username=None, email='ada@example.com')

    assert user.get_display_name() == 'ada@example.com'


def test_the_username_is_optional():
    user = UserFactory(username=None)

    assert user.username is None


def test_several_users_can_have_no_username():
    UserFactory(username=None)
    UserFactory(username=None)

    assert User.objects.filter(username__isnull=True).count() == 2


def test_a_blank_username_is_stored_as_null():
    """Only one row may hold '' in a unique column; any number may hold NULL."""
    user = UserFactory(username='')

    user.refresh_from_db()
    assert user.username is None


def test_the_username_is_still_unique_when_set():
    UserFactory(username='ada')

    with pytest.raises(IntegrityError):
        UserFactory(username='ada')


def test_users_are_identified_by_email():
    user = UserFactory(email='ada@example.com')

    assert User.USERNAME_FIELD == 'email'
    assert user.get_username() == 'ada@example.com'
    assert str(user) == 'ada@example.com'


def test_new_users_are_not_flagged_as_anonymized():
    assert UserFactory().is_anonymized is False


def test_defaults_are_the_least_privileged():
    user = UserFactory()

    assert user.role == user.Role.USER
    assert user.account_type == user.AccountType.FREE
