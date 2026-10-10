import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db

ENV = {
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

    user = User.objects.get(email='admin@example.com')
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


def test_is_idempotent(monkeypatch):
    _run(monkeypatch, ENV)
    _run(monkeypatch, ENV)

    assert User.objects.filter(email='admin@example.com').count() == 1


def test_does_not_clash_with_an_existing_email(monkeypatch):
    UserFactory(email='Admin@example.com', is_superuser=False)

    _run(monkeypatch, ENV)

    assert User.objects.count() == 1
    assert not User.objects.get().is_superuser
