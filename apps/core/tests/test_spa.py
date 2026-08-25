"""The SPA catch-all must serve client routes and nothing else.

Get the regex wrong and it returns index.html with a 200 for things that are
not client routes -- the API, the admin, or a JavaScript bundle. The last of
those is the nastiest: the browser asks for a script, gets HTML, refuses to
execute it, and renders a blank page with no server-side error anywhere.

The pattern pieces are imported from template.urls rather than copied. An
earlier version of this module spelled the regex out again, so the copy here
stayed green while the real one drifted -- which is how `assets/` and a bare
`/admin` came to be swallowed in production.

URLconf is decided at import time from settings.SERVE_SPA, so these tests
build a throwaway URLconf rather than trying to toggle the setting after the
fact.
"""

import pytest
from django.contrib import admin
from django.test import override_settings
from django.urls import include, path, re_path

from apps.core.views import SPAView
from template.urls import SPA_EXCLUDED_PREFIXES, SPA_FILE_LIKE_PATH

SPA_MARKER = '<!doctype html><title>spa</title>'

api_v1_patterns = [
    path('', include('apps.core.urls')),
    path('', include('apps.authentication.urls')),
    path('', include('apps.users.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, 'v1'), namespace='v1')),
    re_path(
        rf'^(?!{SPA_EXCLUDED_PREFIXES})(?!{SPA_FILE_LIKE_PATH}).*$',
        SPAView.as_view(),
        name='spa',
    ),
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


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.parametrize(
    'path',
    [
        '/assets/index-Dk6WSsYO.js',
        '/assets/mui-D-_MVRVW.js',
        '/assets/style-abc123.css',
        '/vite.svg',
        '/favicon.ico',
        '/robots.txt',
        '/manifest.webmanifest',
    ],
)
def test_asset_paths_are_not_served_the_spa(spa_client, path):
    """The white-screen bug.

    WhiteNoise serves these ahead of the URLconf when they exist. When they do
    not, the catch-all used to answer 200 text/html, so the browser received
    HTML where it asked for JavaScript and silently rendered nothing. A 404 is
    the honest answer and shows up in the log.
    """
    response = spa_client.get(path)

    assert response.status_code == 404
    assert SPA_MARKER not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.parametrize('path', ['/favicon.ico/', '/assets/app.js/'])
def test_a_file_path_with_a_trailing_slash_is_not_the_spa_either(spa_client, path):
    """APPEND_SLASH retries the slashed form, which must not become a way in."""
    response = spa_client.get(path)

    assert response.status_code == 404
    assert SPA_MARKER not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_admin_without_a_trailing_slash_redirects_rather_than_returning_the_spa(
    spa_client,
):
    """Excluding only `admin/` left `/admin` resolving to the catch-all.

    Because it resolved, CommonMiddleware never applied APPEND_SLASH, so
    `/admin` answered 200 with index.html instead of reaching the admin.
    """
    response = spa_client.get('/admin')

    assert response.status_code == 301
    assert response['Location'].endswith('/admin/')


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_the_admin_itself_is_not_swallowed(spa_client):
    response = spa_client.get('/admin/')

    # Redirects to the admin login; either way it must not be the SPA.
    assert response.status_code in (200, 302)
    assert SPA_MARKER not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.parametrize(
    'path',
    [
        '/.well-known/oauth-protected-resource',
        '/.well-known/oauth-protected-resource/mcp',
        '/.well-known/openid-configuration',
    ],
)
def test_well_known_paths_are_not_served_the_spa(spa_client, path):
    """Discovery probes must get an honest 404 when nothing is published.

    This URLconf has no metadata route -- MCP_OAUTH_ENABLED adds one, and with
    the flag off there is genuinely nothing there. The catch-all answering
    index.html with a 200 would tell a discovery client the document exists
    and then hand it HTML to parse as JSON, which is a far worse answer than
    "there is nothing here". Hence the exclusion is unconditional rather than
    added with the flag.
    """
    response = spa_client.get(path)

    assert response.status_code == 404
    assert SPA_MARKER not in response.content.decode()
