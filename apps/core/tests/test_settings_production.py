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
    # Required in production. The database cases below are not about origins,
    # so they get a valid one; the origin cases clear it deliberately.
    'FRONTEND_URL': 'https://example.com',
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
    'CORS_ALLOWED_ORIGINS',
    'CSRF_TRUSTED_ORIGINS',
)


@pytest.fixture
def load_production(monkeypatch):
    originals = {
        name: sys.modules.get(name)
        for name in ('clearpath.settings.base', 'clearpath.settings.production')
    }

    def _load(env):
        """Import production under `env`. A value of None leaves that key unset,
        which is how a case opts out of something BASE_ENV supplies."""
        for key in CLEARED:
            monkeypatch.delenv(key, raising=False)
        for key, value in {**BASE_ENV, **env}.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        for name in ('clearpath.settings.base', 'clearpath.settings.production'):
            sys.modules.pop(name, None)
        return importlib.import_module('clearpath.settings.production')

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


def test_a_remote_db_host_without_a_password_is_refused(load_production):
    """The shape a hand-set DB_HOST takes on a managed host.

    DB_NAME falls back to 'app' and DB_PASSWORD to '', neither of which the
    provider created, so the connection can never succeed -- but it fails in
    the entrypoint's retry loop, by which point the platform is reporting an
    unopened port rather than a missing password.
    """
    with pytest.raises(ImproperlyConfigured) as exc:
        load_production({'DB_HOST': 'postgres.railway.internal'})

    message = str(exc.value)
    assert 'postgres.railway.internal' in message
    assert 'DATABASE_URL' in message


def test_a_remote_db_host_with_a_password_is_allowed(load_production):
    """Individually configured remote databases stay a supported path."""
    production = load_production(
        {
            'DB_HOST': 'postgres.example.com',
            'DB_NAME': 'appdb',
            'DB_USER': 'appuser',
            'DB_PASSWORD': 'a-real-password',
        }
    )

    assert production.DATABASES['default']['HOST'] == 'postgres.example.com'


def test_a_local_db_host_without_a_password_is_allowed(load_production):
    """Compose and peer/trust authentication legitimately have no password."""
    production = load_production({'DB_HOST': 'localhost', 'DB_NAME': 'app'})

    assert production.DATABASES['default']['HOST'] == 'localhost'


def test_database_url_is_not_second_guessed_by_the_password_check(load_production):
    """The URL carries its own credentials; an empty DB_PASSWORD is irrelevant."""
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@postgres.railway.internal:5432/railway',
            'DB_PASSWORD': '',
        }
    )

    assert production.DATABASES['default']['NAME'] == 'railway'


def test_the_platform_domain_is_trusted_without_extra_config(load_production):
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.internal:5432/app',
            'RAILWAY_PUBLIC_DOMAIN': 'my-app.up.railway.app',
            # The state a first deploy is in: the platform domain is the only
            # thing available, which is the point of deriving from it.
            'FRONTEND_URL': None,
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


# --------------------------------------------------------------------------
# Origins
#
# base.py derives CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS from
# FRONTEND_URL, whose default is http://localhost:3000. Production shipped
# with that default sitting in both lists while CORS_ALLOW_CREDENTIALS was on.
# --------------------------------------------------------------------------


def test_no_origin_list_carries_the_development_default(load_production):
    """The regression. localhost must not survive into production.

    With CORS_ALLOW_CREDENTIALS on, a leftover http://localhost:3000 tells
    browsers a page on a developer's own machine may make credentialed
    cross-origin requests here and read the responses.
    """
    production = load_production({'DATABASE_URL': 'postgres://u:p@db.example.com:5432/x'})

    origins = production.CORS_ALLOWED_ORIGINS + production.CSRF_TRUSTED_ORIGINS
    assert origins, 'expected the deployment origin, not an empty list'
    assert not any('localhost' in origin for origin in origins)
    assert not any('127.0.0.1' in origin for origin in origins)


def test_the_platform_domain_becomes_the_origin(load_production):
    """A first deploy, with nothing configured but the injected domain."""
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.example.com:5432/x',
            'RAILWAY_PUBLIC_DOMAIN': 'app.up.railway.app',
            'FRONTEND_URL': None,
        }
    )

    assert production.CORS_ALLOWED_ORIGINS == ['https://app.up.railway.app']
    assert production.CSRF_TRUSTED_ORIGINS == ['https://app.up.railway.app']


def test_no_origin_at_all_is_refused(load_production):
    """Neither an explicit origin nor a platform domain.

    Falling back to base.py's http://localhost:3000 here would send password
    reset and verification links to the developer's own machine, and silently.
    """
    with pytest.raises(ImproperlyConfigured) as exc:
        load_production(
            {
                'DATABASE_URL': 'postgres://u:p@db.example.com:5432/x',
                'FRONTEND_URL': None,
            }
        )

    message = str(exc.value)
    assert 'FRONTEND_URL' in message
    assert 'localhost' in message


def test_an_explicit_frontend_url_drives_both_lists(load_production):
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.example.com:5432/x',
            'FRONTEND_URL': 'https://app.example.com',
        }
    )

    assert production.CORS_ALLOWED_ORIGINS == ['https://app.example.com']
    assert production.CSRF_TRUSTED_ORIGINS == ['https://app.example.com']
    assert production.FRONTEND_URL == 'https://app.example.com'


def test_explicit_origin_lists_win_over_the_frontend_url(load_production):
    production = load_production(
        {
            'DATABASE_URL': 'postgres://u:p@db.example.com:5432/x',
            'FRONTEND_URL': 'https://app.example.com',
            'CORS_ALLOWED_ORIGINS': 'https://a.example.com,https://b.example.com',
            'CSRF_TRUSTED_ORIGINS': 'https://c.example.com',
        }
    )

    assert production.CORS_ALLOWED_ORIGINS == [
        'https://a.example.com',
        'https://b.example.com',
    ]
    assert production.CSRF_TRUSTED_ORIGINS == ['https://c.example.com']
