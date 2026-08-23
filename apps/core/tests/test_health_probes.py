"""Platform health probes.

The first Railway deploy's healthcheck could not have passed even once the
database was fixed: the probe arrives over plain HTTP with the platform's own
Host header, so production answered 301 (SECURE_SSL_REDIRECT) or 400
(DisallowedHost) instead of the 200 the probe requires.

HealthCheckMiddleware runs before both. These tests pin that it answers, and
equally that it does not weaken anything else.
"""

import pytest
from django.test import Client, override_settings

HEALTH = '/api/v1/health/'
READY = '/api/v1/ready/'

# Deliberately excludes every host the probes are tried with below.
PROD_HOSTS = ['my-app.up.railway.app']


def _prod(**extra):
    return override_settings(
        ALLOWED_HOSTS=PROD_HOSTS,
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        **extra,
    )


@pytest.mark.parametrize(
    'host',
    [
        'healthcheck.railway.app',  # Railway
        '10.0.0.7',  # container IP, as k8s and others probe
        'anything.internal',
    ],
)
def test_liveness_answers_an_unknown_probe_host_over_plain_http(host):
    with _prod():
        response = Client().get(HEALTH, HTTP_HOST=host)

    assert response.status_code == 200
    assert response.json()['data']['status'] == 'ok'


@pytest.mark.django_db
def test_readiness_answers_an_unknown_probe_host_over_plain_http():
    with _prod():
        response = Client().get(READY, HTTP_HOST='healthcheck.railway.app')

    assert response.status_code == 200
    assert response.json()['data']['checks']['database'] is True


def test_liveness_is_not_redirected_to_https():
    # SECURE_SSL_REDIRECT would otherwise turn the probe into a 301, which
    # Railway counts as a failed healthcheck.
    with _prod():
        response = Client().get(HEALTH, HTTP_HOST='my-app.up.railway.app')

    assert response.status_code == 200


def test_a_normal_route_still_rejects_an_unknown_host():
    with _prod():
        response = Client().get('/api/v1/auth/csrf/', HTTP_HOST='evil.example.com')

    assert response.status_code == 400


def test_a_normal_route_is_still_redirected_to_https():
    with _prod():
        response = Client().get('/api/v1/auth/csrf/', HTTP_HOST='my-app.up.railway.app')

    assert response.status_code == 301
    assert response['Location'].startswith('https://')


@pytest.mark.django_db
def test_readiness_reports_a_failing_database(monkeypatch):
    monkeypatch.setattr('apps.core.middleware.check_database', lambda: False)

    with _prod():
        response = Client().get(READY, HTTP_HOST='healthcheck.railway.app')

    # 503 so a platform readiness probe actually pulls the instance out.
    assert response.status_code == 503
    assert response.json()['data']['checks']['database'] is False


def test_the_probe_paths_match_the_urlconf():
    """The middleware matches literal paths, so a route rename must break here."""
    from django.urls import reverse

    assert reverse('v1:health') == HEALTH
    assert reverse('v1:readiness') == READY


@pytest.mark.parametrize(
    'settings_module',
    [
        'template.settings.base',
        'template.settings.development',
        'template.settings.production',
        'template.settings.testing',
    ],
)
def test_the_probe_middleware_runs_before_the_security_middleware(settings_module):
    """Ordering is the whole fix, so assert it rather than trusting a comment.

    Development puts debug_toolbar ahead of it, which is fine -- what matters
    is only that it precedes SecurityMiddleware's SSL redirect and host
    validation.
    """
    import importlib
    import os
    import sys

    for key, value in {
        'SECRET_KEY': 'test-key-long-enough-000000000000000000000000',
        'ALLOWED_HOSTS': 'example.com',
        'DATABASE_URL': 'postgres://u:p@db.example.com:5432/app',
        # Production refuses to fall back to a localhost origin.
        'FRONTEND_URL': 'https://example.com',
    }.items():
        os.environ.setdefault(key, value)

    sys.modules.pop(settings_module, None)
    module = importlib.import_module(settings_module)
    middleware = module.MIDDLEWARE

    health = next(i for i, m in enumerate(middleware) if 'HealthCheckMiddleware' in m)
    security = next(
        (i for i, m in enumerate(middleware) if m.endswith('SecurityMiddleware')), None
    )

    assert security is None or health < security, (
        f'{settings_module}: HealthCheckMiddleware must precede SecurityMiddleware'
    )
