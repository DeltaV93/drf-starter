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
    _run(monkeypatch, {'DJANGO_SUPERUSER_USERNAME': 'admin'})

    assert User.objects.count() == 0


def test_is_idempotent(monkeypatch):
    _run(monkeypatch, ENV)
    _run(monkeypatch, ENV)

    assert User.objects.filter(username='admin').count() == 1


def test_does_not_clash_with_an_existing_email(monkeypatch):
    UserFactory(username='someone-else', email='admin@example.com')

    _run(monkeypatch, ENV)

    assert not User.objects.filter(username='admin').exists()
