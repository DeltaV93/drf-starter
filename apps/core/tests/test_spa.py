"""The SPA catch-all must not swallow the API.

The catch-all in template/urls.py is registered last and excludes api/,
admin/, static/ and media/. Get that regex wrong and every endpoint starts
returning index.html with a 200, which no other test would notice.

URLconf is decided at import time from settings.SERVE_SPA, so these tests
build a throwaway URLconf rather than trying to toggle the setting after the
fact.
"""

import pytest
from django.test import override_settings
from django.urls import include, path, re_path

from apps.core.views import SPAView

SPA_MARKER = '<!doctype html><title>spa</title>'

api_v1_patterns = [
    path('', include('apps.core.urls')),
    path('', include('apps.authentication.urls')),
    path('', include('apps.users.urls')),
]

urlpatterns = [
    path('api/v1/', include((api_v1_patterns, 'v1'), namespace='v1')),
    re_path(r'^(?!api/|admin/|static/|media/|__debug__/).*$', SPAView.as_view(), name='spa'),
]


@pytest.fixture
def spa_client(client, tmp_path, settings):
    """A client using the catch-all URLconf and a stand-in index.html."""
    (tmp_path / 'index.html').write_text(SPA_MARKER)
    settings.TEMPLATES = [
        {
            **settings.TEMPLATES[0],
            'DIRS': [tmp_path],
        }
    ]
    return client


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.parametrize(
    'route', ['/', '/login', '/signup', '/profile', '/confirm-password/a/b']
)
def test_client_routes_return_the_spa(spa_client, route):
    response = spa_client.get(route)

    assert response.status_code == 200
    assert SPA_MARKER in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_the_api_is_not_swallowed(spa_client):
    response = spa_client.get('/api/v1/health/')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')
    assert SPA_MARKER not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_an_unknown_api_path_404s_rather_than_returning_the_spa(spa_client):
    # Without the api/ exclusion this would be a 200 of index.html, and a
    # frontend bug calling a wrong path would look like a working request.
    response = spa_client.get('/api/v1/does-not-exist/')

    assert response.status_code == 404
    assert SPA_MARKER not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_auth_endpoints_still_answer_as_json(spa_client):
    response = spa_client.get('/api/v1/auth/csrf/')

    assert response.status_code == 200
    assert response.json()['status'] == 'success'
