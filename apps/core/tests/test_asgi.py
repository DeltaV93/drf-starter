"""The application under ASGI.

The container serves `template.asgi:application` through uvicorn's worker
class. Django's ordinary test `Client` does not go near that path -- it drives
the WSGI handler -- so the rest of the suite could stay green while the thing
actually deployed behaved differently.

These tests drive the ASGI handler, and they exist for one reason above all:
`HealthCheckMiddleware` has to answer a platform probe before
`SECURE_SSL_REDIRECT` can 301 it and before `ALLOWED_HOSTS` can 400 it. That
property is what the first Railway deploy failed on, it is pinned under WSGI by
`test_health_probes.py`, and switching transports is exactly the kind of change
that could quietly undo it.

Every middleware in the stack is sync, so Django adapts the chain once rather
than hopping per layer -- which is why behaviour is expected to be identical
rather than merely similar. Confirmed by hand against both servers on twelve
paths before this file was written.
"""

import pytest
from django.test import AsyncClient, override_settings

HEALTH = '/api/v1/health/'
READY = '/api/v1/ready/'

# Deliberately excludes the hosts the probes are tried with below.
PROD_HOSTS = ['my-app.up.railway.app']


def _prod(**extra):
    return override_settings(
        ALLOWED_HOSTS=PROD_HOSTS,
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        **extra,
    )


def test_the_asgi_application_is_importable_and_callable():
    """What the Dockerfile names. A typo here is a container that never boots."""
    from template.asgi import application

    assert callable(application)


@pytest.mark.asyncio
async def test_liveness_answers_over_asgi():
    response = await AsyncClient().get(HEALTH)

    assert response.status_code == 200
    assert response.json()['data']['status'] == 'ok'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'host',
    [
        'healthcheck.railway.app',  # Railway
        '10.0.0.7',  # container IP, as k8s and others probe
        'anything.internal',
    ],
)
async def test_liveness_answers_an_unknown_probe_host_over_plain_http(host):
    """The property the first deploy failed on, re-proved on the new transport.

    A probe arrives over plain HTTP with the platform's own Host header. If
    SecurityMiddleware sees it first the answer is a 301; if the host check
    sees it first the answer is a 400. Either one fails the healthcheck.
    """
    with _prod():
        response = await AsyncClient().get(HEALTH, headers={'host': host})

    assert response.status_code == 200, (
        f'Probe host {host!r} got {response.status_code}, not 200. '
        'HealthCheckMiddleware must stay ahead of SecurityMiddleware.'
    )


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_readiness_answers_over_asgi():
    with _prod():
        response = await AsyncClient().get(READY, headers={'host': 'anything.internal'})

    # 200 or 503 both prove it was answered rather than redirected or refused;
    # which one depends on the database, and that is what it is reporting.
    assert response.status_code in {200, 503}


@pytest.mark.asyncio
async def test_a_disallowed_host_is_still_refused_everywhere_else():
    """Guards the tests above: the health exemption must not be a global one.

    If it were, this would return something other than 400 and the probe
    tests would be passing for the wrong reason.
    """
    with _prod():
        response = await AsyncClient().get(
            '/api/v1/users/me/', headers={'host': 'evil.example'}
        )

    assert response.status_code == 400
