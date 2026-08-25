"""Discovery: how a client that knows only this URL finds its way in.

Without a correct metadata document, connecting an MCP client means somebody
pasting an issuer URL by hand -- the difference between a server anyone can add
and one only its author can configure. These tests pin the parts a client
actually parses.
"""

from unittest.mock import patch

import pytest
from django.core.cache.backends.base import BaseCache
from django.test import Client, override_settings
from rest_framework.throttling import AnonRateThrottle

from apps.mcp_oauth.metadata import WELL_KNOWN, document, metadata_url
from apps.mcp_oauth.views import ProtectedResourceMetadataView

from .keys import AUDIENCE, ISSUER, settings_ok

PATH = f'{WELL_KNOWN}/mcp'


def test_the_document_is_readable_without_a_credential():
    """The point of it. A client reads this *before* it has a token, so any
    authentication on it would make discovery impossible."""
    with settings_ok:
        response = Client().get(PATH)

    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('application/json')


def test_the_document_names_the_authorization_server():
    with settings_ok:
        body = Client().get(PATH).json()

    assert body['authorization_servers'] == [ISSUER]
    assert body['resource'] == AUDIENCE


def test_the_document_is_not_wrapped_in_the_api_envelope():
    """The one deliberate exception to the project's response convention.

    RFC 9728 fixes this document's shape. A client looks for
    `authorization_servers` at the top level, and `{status, message, data,
    errors}` would bury it -- so the exception is pinned here rather than left
    for someone to "fix" into consistency later.
    """
    with settings_ok:
        body = Client().get(PATH).json()

    assert 'data' not in body
    assert 'status' not in body
    assert 'authorization_servers' in body


def test_a_token_is_only_accepted_in_the_header():
    """A token in a query string is written into every access log and Referer
    header between the client and here."""
    with settings_ok:
        body = Client().get(PATH).json()

    assert body['bearer_methods_supported'] == ['header']


def test_the_bare_well_known_path_serves_the_same_document():
    """A resource identifier with no path derives exactly this URL, and clients
    have been observed to try it first."""
    with settings_ok:
        with_path = Client().get(PATH).json()
        bare = Client().get(WELL_KNOWN).json()

    assert bare == with_path


@pytest.mark.parametrize(
    ('resource', 'expected'),
    [
        (
            'https://app.example.test/mcp',
            f'https://app.example.test{WELL_KNOWN}/mcp',
        ),
        (
            'https://app.example.test/mcp/',
            f'https://app.example.test{WELL_KNOWN}/mcp',
        ),
        ('https://app.example.test', f'https://app.example.test{WELL_KNOWN}'),
        ('https://app.example.test/', f'https://app.example.test{WELL_KNOWN}'),
    ],
)
def test_the_well_known_segment_is_inserted_not_appended(resource, expected):
    """The derivation that is easy to get backwards.

    RFC 9728 puts the well-known segment *between* the origin and the
    resource's path, the same way RFC 8414 does for authorization servers.
    Appending it instead produces a URL that looks plausible and that no
    client will ever request.
    """
    with override_settings(MCP_OAUTH_AUDIENCE=resource):
        assert metadata_url() == expected


def test_the_document_survives_a_resource_with_a_port():
    with override_settings(MCP_OAUTH_AUDIENCE='http://localhost:8000/mcp'):
        assert metadata_url() == f'http://localhost:8000{WELL_KNOWN}/mcp'


def test_the_advertised_scopes_are_configurable():
    """A deployment that carves its tool surface differently has to be able to
    say so, or clients ask for scopes the authorization server will not grant."""
    with override_settings(MCP_OAUTH_SCOPES_SUPPORTED=['files:read']):
        assert document()['scopes_supported'] == ['files:read']


class BrokenCache(BaseCache):
    """A cache backend that behaves the way an unreachable Redis does."""

    def __init__(self, location, params):
        super().__init__(params)

    def get(self, *args, **kwargs):
        raise ConnectionError('Redis is down')

    def set(self, *args, **kwargs):
        raise ConnectionError('Redis is down')


broken_cache = override_settings(CACHES={'default': {'BACKEND': f'{__name__}.BrokenCache'}})


def test_discovery_survives_the_cache_being_down():
    """Observed, not theorised.

    The default AnonRateThrottle reads the cache on every request, so with
    Redis unreachable this endpoint answered 500 -- and a client that cannot
    read this document cannot authenticate at all, so discovery is the last
    thing that should depend on the cache being up. The view declares no
    throttle classes for exactly that reason.

    The guard is in the same test: the *only* difference between the two calls
    below is that declaration. Without it, one assertion would pass whether or
    not the broken cache was ever reached.
    """
    view = ProtectedResourceMetadataView

    with settings_ok, broken_cache:
        # Throttled: the broken cache is genuinely on the path.
        with patch.object(view, 'throttle_classes', [AnonRateThrottle]):
            with pytest.raises(ConnectionError):
                Client().get(PATH)

        # As shipped.
        response = Client().get(PATH)

    assert response.status_code == 200
    assert response.json()['authorization_servers']
