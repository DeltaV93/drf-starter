"""The router in template/asgi.py.

Two applications behind one port. Getting the split wrong in either direction
is quiet: MCP paths falling through to Django would be answered by the SPA
catch-all with a 200 and a page of HTML, and Django paths captured by MCP would
break the entire application.
"""

import pytest
from django.test import override_settings


def _scope(path):
    return {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': b'',
        'root_path': '',
        'headers': [(b'host', b'testserver')],
        'client': ('127.0.0.1', 0),
        'server': ('testserver', 80),
    }


def _routed_to(path):
    """Which application the *real* router hands `path` to.

    Drives `clearpath.asgi._with_mcp` itself with a stub Django app. Rebuilding
    the dispatch rule here instead would only prove that a copy of the rule
    agrees with itself.
    """
    import asyncio

    from clearpath.asgi import _with_mcp

    reached_django = False

    async def stub_django(scope, receive, send):
        nonlocal reached_django
        reached_django = True

    router = _with_mcp(stub_django)

    async def drive():
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                await asyncio.Event().wait()
            sent = True
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        async def send(message):
            pass

        try:
            # The MCP app may refuse the request for its own reasons (no
            # session, wrong accept header). That is fine: what is being
            # measured is which application was handed the request.
            await asyncio.wait_for(router(_scope(path), receive, send), timeout=5)
        except Exception:
            pass

    asyncio.run(drive())
    return 'django' if reached_django else 'mcp'


@pytest.mark.parametrize('path', ['/mcp', '/mcp/', '/mcp/messages', '/mcp/anything/deeper'])
def test_mcp_paths_reach_the_mcp_app(path):
    assert _routed_to(path) == 'mcp'


@pytest.mark.parametrize(
    'path',
    [
        '/',
        '/api/v1/health/',
        '/api/v1/users/me/',
        '/admin/',
        '/assets/index.js',
        '/login',
        # The one a naive prefix test gets wrong: a different route that
        # merely starts with the same letters.
        '/mcp-docs',
        '/mcpx',
    ],
)
def test_everything_else_reaches_django(path):
    assert _routed_to(path) == 'django'


def test_the_router_is_absent_when_the_flag_is_off():
    """With MCP off, `application` is Django's own ASGI app and serving is
    exactly what it was before MCP existed."""
    import importlib

    import clearpath.asgi as asgi

    with override_settings(MCP_SERVER_ENABLED=False):
        reloaded = importlib.reload(asgi)
        assert reloaded.application is reloaded.django_application

    # Put the module back the way the rest of the suite expects it.
    importlib.reload(asgi)
