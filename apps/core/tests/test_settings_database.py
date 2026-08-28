"""Database configuration resolution.

Managed hosts hand over a single DATABASE_URL; local development and docker
compose use the individual DB_* variables. base.py has to honour both, and
the settings module is only imported once per process, so these tests
re-import it under a patched environment rather than inspecting the live one.
"""

import importlib
import sys

import pytest


def _load_base(monkeypatch, env):
    """Import clearpath.settings.base fresh with exactly `env` applied."""
    for key in (
        'DATABASE_URL',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'DB_SSL_REQUIRE',
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setitem(sys.modules, 'clearpath.settings.base', None)
    del sys.modules['clearpath.settings.base']
    module = importlib.import_module('clearpath.settings.base')
    return module


@pytest.fixture(autouse=True)
def _restore_base():
    original = sys.modules.get('clearpath.settings.base')
    yield
    if original is not None:
        sys.modules['clearpath.settings.base'] = original


def test_database_url_wins_when_present(monkeypatch):
    base = _load_base(
        monkeypatch,
        {
            'DATABASE_URL': 'postgres://alice:s3cret@db.example.com:6543/appdb',
            # Deliberately conflicting: DATABASE_URL must take precedence.
            'DB_NAME': 'ignored',
            'DB_HOST': 'ignored.example',
        },
    )
    default = base.DATABASES['default']

    assert default['NAME'] == 'appdb'
    assert default['USER'] == 'alice'
    assert default['HOST'] == 'db.example.com'
    assert default['PORT'] == 6543


def test_a_remote_database_url_requires_ssl(monkeypatch):
    base = _load_base(
        monkeypatch, {'DATABASE_URL': 'postgres://u:p@db.example.com:5432/appdb'}
    )

    assert base.DATABASES['default']['OPTIONS']['sslmode'] == 'require'


def test_a_local_database_url_does_not_require_ssl(monkeypatch):
    # Local Postgres and the compose `db` service do not speak TLS, so
    # defaulting sslmode=require there would break every local run.
    base = _load_base(monkeypatch, {'DATABASE_URL': 'postgres://u:p@localhost:5432/appdb'})

    assert 'sslmode' not in base.DATABASES['default'].get('OPTIONS', {})


def test_compose_host_is_treated_as_local(monkeypatch):
    base = _load_base(monkeypatch, {'DATABASE_URL': 'postgres://u:p@db:5432/appdb'})

    assert 'sslmode' not in base.DATABASES['default'].get('OPTIONS', {})


def test_individual_variables_are_used_without_a_url(monkeypatch):
    base = _load_base(
        monkeypatch,
        {'DB_NAME': 'localdb', 'DB_USER': 'localuser', 'DB_HOST': '127.0.0.1'},
    )
    default = base.DATABASES['default']

    assert default['NAME'] == 'localdb'
    assert default['USER'] == 'localuser'
    assert default['HOST'] == '127.0.0.1'
    assert default['ENGINE'] == 'django.db.backends.postgresql'
