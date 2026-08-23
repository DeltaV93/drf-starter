"""The health endpoints as ordinary callers see them.

HealthCheckMiddleware answers these paths before URL resolution, so the
responses are plain JsonResponses rather than DRF ones -- the envelope is
identical either way, which is what these assert. Probe-specific behaviour
(unknown Host, plain HTTP) lives in test_health_probes.py.
"""

import pytest
from django.urls import reverse


def test_health_is_public(client):
    response = client.get(reverse('v1:health'))

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'success'
    assert body['data']['status'] == 'ok'


@pytest.mark.django_db
def test_readiness_reports_database(client):
    response = client.get(reverse('v1:readiness'))

    assert response.status_code == 200
    assert response.json()['data']['checks']['database'] is True


@pytest.mark.django_db
def test_the_view_and_the_middleware_answer_identically(client, settings):
    """The view is a fallback, so it must not drift from the middleware."""
    through_middleware = client.get(reverse('v1:health')).json()

    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if 'HealthCheckMiddleware' not in m]
    through_view = client.get(reverse('v1:health')).json()

    assert through_middleware == through_view
