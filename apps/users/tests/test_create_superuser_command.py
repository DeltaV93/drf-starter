import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db

ENV = {
    'DJANGO_SUPERUSER_USERNAME': 'admin',
    'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
    'DJANGO_SUPERUSER_PASSWORD': 'a-real-admin-passphrase',
}


def _run(monkeypatch, env):
    for key in ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    call_command('create_superuser_if_not_exists')


def test_creates_a_superuser_from_the_environment(monkeypatch):
    _run(monkeypatch, ENV)

    user = User.objects.get(username='admin')
    assert user.is_superuser
    assert user.email_verified is True
    assert user.check_password('a-real-admin-passphrase')


def test_does_nothing_without_the_environment_variables(monkeypatch):
    # The old version hard-coded admin/admin and created it unconditionally.
    _run(monkeypatch, {})

    assert User.objects.count() == 0


def test_does_nothing_when_only_some_variables_are_set(monkeypatch):
    _run(monkeypatch, {'DJANGO_SUPERUSER_EMAIL': 'admin@example.com'})

    assert User.objects.count() == 0


def test_the_username_is_optional(monkeypatch):
    """An address and a password are all an account needs."""
    _run(
        monkeypatch,
        {k: v for k, v in ENV.items() if k != 'DJANGO_SUPERUSER_USERNAME'},
    )

    user = User.objects.get(email='admin@example.com')
    assert user.is_superuser
    assert user.username is None
    assert user.check_password('a-real-admin-passphrase')


def test_does_not_clash_with_an_existing_username(monkeypatch):
    UserFactory(username='admin', email='someone-else@example.com')

    _run(monkeypatch, ENV)

    assert not User.objects.filter(email='admin@example.com').exists()


def test_is_idempotent(monkeypatch):
    _run(monkeypatch, ENV)
    _run(monkeypatch, ENV)

    assert User.objects.filter(username='admin').count() == 1


def test_does_not_clash_with_an_existing_email(monkeypatch):
    UserFactory(username='someone-else', email='admin@example.com')

    _run(monkeypatch, ENV)

    assert not User.objects.filter(username='admin').exists()


def test_does_not_clash_with_an_existing_email_of_another_case(monkeypatch):
    UserFactory(email='ADMIN@example.com')

    _run(monkeypatch, ENV)

    assert User.objects.count() == 1


def test_djangos_own_createsuperuser_needs_only_an_address(monkeypatch):
    """`createsuperuser` prompts for USERNAME_FIELD plus REQUIRED_FIELDS.

    Both moved -- the identifier is the email and nothing else is required --
    and the manager it calls no longer takes the username first.
    """
    monkeypatch.setenv('DJANGO_SUPERUSER_PASSWORD', 'a-real-admin-passphrase')

    call_command('createsuperuser', interactive=False, email='root@example.com')

    user = User.objects.get(email='root@example.com')
    assert user.is_superuser and user.is_staff
    assert user.username is None
    assert user.check_password('a-real-admin-passphrase')
