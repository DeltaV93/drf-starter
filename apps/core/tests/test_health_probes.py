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
