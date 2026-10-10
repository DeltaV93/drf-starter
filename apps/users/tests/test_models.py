import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError

from apps.users.factories import DEFAULT_PASSWORD, UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_the_email_address_is_the_username():
    assert User.USERNAME_FIELD == 'email'
    assert User.REQUIRED_FIELDS == []
    with pytest.raises(FieldDoesNotExist):
        User._meta.get_field('username')


def test_email_is_unique():
    UserFactory(email='taken@example.com')

    with pytest.raises(IntegrityError):
        UserFactory(email='taken@example.com')


def test_email_is_unique_regardless_of_case():
    # Bypasses the manager's normalisation: the database is the backstop for
    # any write path that forgets it.
    UserFactory(email='taken@example.com')

    with pytest.raises(IntegrityError):
        UserFactory(email='Taken@Example.com')


def test_create_user_normalises_the_email():
    user = User.objects.create_user(email='  Ada@Example.COM ', password=DEFAULT_PASSWORD)

    assert user.email == 'ada@example.com'
    assert user.check_password(DEFAULT_PASSWORD)
    assert not user.is_staff
    assert not user.is_superuser


def test_create_user_requires_an_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email='', password=DEFAULT_PASSWORD)


def test_create_superuser_sets_the_flags():
    user = User.objects.create_superuser(email='root@example.com', password=DEFAULT_PASSWORD)

    assert user.is_staff
    assert user.is_superuser


def test_create_superuser_refuses_to_create_a_non_staff_superuser():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email='root@example.com', password=DEFAULT_PASSWORD, is_staff=False
        )


def test_sign_in_matches_the_email_without_regard_to_case():
    user = UserFactory(email='ada@example.com')

    assert authenticate(email='ADA@example.com', password=DEFAULT_PASSWORD) == user


def test_display_name_prefers_the_full_name():
    user = UserFactory(first_name='Ada', last_name='Lovelace')

    assert user.get_display_name() == 'Ada Lovelace'


def test_display_name_falls_back_to_the_email():
    user = UserFactory(first_name='', last_name='', email='ada@example.com')

    assert user.get_display_name() == 'ada@example.com'


def test_new_users_are_not_flagged_as_anonymized():
    assert UserFactory().is_anonymized is False


def test_defaults_are_the_least_privileged():
    user = UserFactory()

    assert user.role == user.Role.USER
    assert user.account_type == user.AccountType.FREE
