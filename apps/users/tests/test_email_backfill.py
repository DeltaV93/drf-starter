"""The data migration that lowercases addresses already in the table.

Exercised by calling the migration's own function against the live model
registry. Rows are seeded with `.update()`, which is the only way to get a
mixed-case address past `CustomUser.save()` -- and is also exactly how such a
row came to exist on a deployment that predates this change.
"""

from importlib import import_module

import pytest
from django.apps import apps as global_apps
from django.contrib.auth import get_user_model

from apps.users.factories import UserFactory

# import_module because a module name cannot start with a digit.
lowercase_emails = import_module(
    'apps.users.migrations.0003_lowercase_emails'
).lowercase_emails

User = get_user_model()

pytestmark = pytest.mark.django_db


def _store_raw(user, email):
    """Put an address in the column without going through save()."""
    User.objects.filter(pk=user.pk).update(email=email)
    user.refresh_from_db()
    return user


def test_a_mixed_case_address_is_lowercased():
    user = _store_raw(UserFactory(), 'Ada@Example.COM')

    lowercase_emails(global_apps, None)

    user.refresh_from_db()
    assert user.email == 'ada@example.com'


def test_addresses_already_lowercase_are_left_alone():
    user = UserFactory(email='ada@example.com')

    lowercase_emails(global_apps, None)

    user.refresh_from_db()
    assert user.email == 'ada@example.com'


def test_a_row_whose_lowercase_form_is_taken_is_left_as_it_is(capsys):
    """Two accounts for one person. Which survives is not a migration's call.

    Lowercasing blindly would hit the unique constraint and fail the deploy.
    """
    lower = UserFactory(email='ada@example.com')
    upper = _store_raw(UserFactory(), 'ADA@example.com')

    lowercase_emails(global_apps, None)

    lower.refresh_from_db()
    upper.refresh_from_db()
    assert lower.email == 'ada@example.com'
    assert upper.email == 'ADA@example.com'
    assert 'ADA@example.com' in capsys.readouterr().out


def test_the_other_rows_are_still_migrated_around_a_collision():
    UserFactory(email='ada@example.com')
    collides = _store_raw(UserFactory(), 'ADA@example.com')
    ordinary = _store_raw(UserFactory(), 'Grace@Example.com')

    lowercase_emails(global_apps, None)

    collides.refresh_from_db()
    ordinary.refresh_from_db()
    assert collides.email == 'ADA@example.com'
    assert ordinary.email == 'grace@example.com'
