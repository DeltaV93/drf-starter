"""Which Host headers the endpoint answers to.

The SDK turns DNS-rebinding protection on by default and defaults its
allow-list to `127.0.0.1`. That is right for what it was written for -- a
local server a browser could otherwise be tricked into addressing -- and wrong
for a deployed application, where every request arrives with a real domain in
the Host header and gets **421 Misdirected Request** from an endpoint that
mounted perfectly and logged nothing wrong.

The allow-list is derived from ALLOWED_HOSTS instead, so there is nothing new
to configure and nothing that can drift from the Django side of the same
question. These tests are what keep that true.
"""

import pytest
from django.conf import settings
from django.test import override_settings

pytestmark = pytest.mark.skipif(
    not settings.MCP_SERVER_ENABLED, reason='the MCP server is switched off'
)


def _security():
    from apps.mcp_server.asgi import _transport_security

    return _transport_security()


@override_settings(ALLOWED_HOSTS=['app.example.com'])
def test_a_deployed_domain_is_allowed():
    """The bug this file exists for: without this, a deployed endpoint answers
    421 to every request."""
    assert 'app.example.com' in _security().allowed_hosts


@override_settings(ALLOWED_HOSTS=['app.example.com'])
def test_the_same_domain_with_a_port_is_allowed():
    """`example.com` and `example.com:443` are the same deployment, and a
    proxy that keeps the port would otherwise be refused."""
    assert 'app.example.com:*' in _security().allowed_hosts


@override_settings(ALLOWED_HOSTS=['.example.com'])
def test_a_wildcard_subdomain_entry_loses_its_leading_dot():
    """Django spells "any subdomain" with a leading dot. The MCP middleware
    compares Host headers literally, and no Host header starts with one."""
    assert '.example.com' not in _security().allowed_hosts
    assert 'example.com' in _security().allowed_hosts


@override_settings(ALLOWED_HOSTS=['app.example.com'])
def test_an_unlisted_host_is_not_allowed():
    """Guards the tests above: the allow-list must still be a list."""
    assert 'attacker.example' not in _security().allowed_hosts
    assert _security().enable_dns_rebinding_protection


@override_settings(ALLOWED_HOSTS=['*'])
def test_a_django_wildcard_disables_the_check_rather_than_listing_a_star():
    """Django is already accepting any host, so there is no narrower answer.
    An allow-list containing the literal '*' would match nothing at all, which
    is the worst of both."""
    security = _security()

    assert not security.enable_dns_rebinding_protection
    assert '*' not in security.allowed_hosts


@override_settings(
    ALLOWED_HOSTS=['app.example.com'],
    CSRF_TRUSTED_ORIGINS=['https://app.example.com'],
    FRONTEND_URL='https://www.example.com',
)
def test_origins_come_from_the_settings_that_already_answer_that_question():
    origins = _security().allowed_origins

    assert 'https://app.example.com' in origins
    assert 'https://www.example.com' in origins


# ---------------------------------------------------------------------------
# The whole way through.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@override_settings(ALLOWED_HOSTS=['app.example.com'])
async def test_a_real_client_reaches_the_endpoint_on_a_deployed_domain():
    """Not a unit test of the allow-list: a genuine MCP handshake with a real
    domain in the Host header, which is the request that used to 421."""
    from .test_transport_end_to_end import _application, _connect, _LifespanApp

    app = _application()

    async with _LifespanApp(app):
        async for session in _connect(app, 'http://app.example.com/mcp'):
            listing = await session.list_tools()

    assert [tool.name for tool in listing.tools]
