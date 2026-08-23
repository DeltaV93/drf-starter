"""Production configuration guards.

These exist because a missing DATABASE_URL on Railway did not fail loudly --
base.py fell back to DB_HOST=localhost and the container spent minutes
retrying a connection to 127.0.0.1 before dying with a traceback, when the
real problem was one unset variable.

production.py is imported for its side effects, so each case re-imports it
under a patched environment.
"""

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

BASE_ENV = {
    'SECRET_KEY': 'test-key-long-enough-not-to-trip-the-deploy-check-000000',
    'ALLOWED_HOSTS': 'example.com',
}

CLEARED = (
    'DATABASE_URL',
    'DB_HOST',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'DB_PORT',
    'RAILWAY_PUBLIC_DOMAIN',
    'RENDER_EXTERNAL_HOSTNAME',
    'FLY_APP_NAME',
    'FRONTEND_URL',
)


@pytest.fixture
def load_production(monkeypatch):
    originals = {
        name: sys.modules.get(name)
        for name in ('template.settings.base', 'template.settings.production')
    }

    def _load(env):
        for key in CLEARED:
            monkeypatch.delenv(key, raising=False)
        for key, value in {**BASE_ENV, **env}.items():
            monkeypatch.setenv(key, value)
        for name in ('template.settings.base', 'template.settings.production'):
            sys.modules.pop(name, None)
        return importlib.import_module('template.settings.production')

    yield _load

    for name, module in originals.items():
        if module is not None:
            sys.modules[name] = module


def test_an_unconfigured_database_is_refused(load_production):
    with pytest.raises(ImproperlyConfigured) as exc:
        load_production({})

    message = str(exc.value)
    assert 'DATABASE_URL' in message
    # The message has to name the fix, not just the symptom.
    assert 'Railway' in message
    assert 'localhost' in message


def test_database_url_satisfies_the_guard(load_production):
    production = load_production(
        {'DATABASE_URL': 'postgres://u:p@db.railway.internal:5432/railway'}
    )

    assert production.DATABASES['default']['HOST'] == 'db.railway.internal'


def test_individual_db_variables_satisfy_the_guard(load_production):
    production = load_production({'DB_HOST': 'db', 'DB_NAME': 'app'})

    assert production.DATABASES['default']['HOST'] == 'db'


def test_the_platform_domain_is_trusted_without_extra_config(load_production):
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.internal:5432/app',
            'RAILWAY_PUBLIC_DOMAIN': 'my-app.up.railway.app',
        }
    )

    assert 'my-app.up.railway.app' in production.ALLOWED_HOSTS
    assert 'https://my-app.up.railway.app' in production.CSRF_TRUSTED_ORIGINS
    # The SPA is same-origin, so emailed links point at the same domain.
    assert production.FRONTEND_URL == 'https://my-app.up.railway.app'


def test_an_explicit_frontend_url_is_not_overridden(load_production):
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.internal:5432/app',
            'RAILWAY_PUBLIC_DOMAIN': 'my-app.up.railway.app',
            'FRONTEND_URL': 'https://www.example.com',
        }
    )

    assert production.FRONTEND_URL == 'https://www.example.com'
