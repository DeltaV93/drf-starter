"""A real MCP client, speaking to the real endpoint.

Every other test in this app calls a tool function directly. That proves the
tools are right and proves nothing about whether anything can *reach* them --
and the difference is not academic. The endpoint shipped in a state where it
mounted cleanly, accepted a connection, spoke JSON-RPC and answered every
single call with "Task group is not initialized", because the SDK's Starlette
app declares `lifespan=session_manager.run()` and the ASGI router was sending
the lifespan scope to Django, which rejects anything but `http`.

Nothing caught it. A unit test could not: the failure is in the wiring between
two applications, and it only appears when something completes a handshake.

So this file drives the genuine `mcp` client over the genuine ASGI app,
in process, with no server and no socket -- the transport is `httpx2`'s
ASGI one. It runs in CI like anything else.
"""

import pytest
from django.conf import settings

pytestmark = pytest.mark.skipif(
    not settings.MCP_SERVER_ENABLED, reason='the MCP server is switched off'
)


class _LifespanApp:
    """Drives an ASGI app's lifespan, then serves requests through it.

    A real server does this: startup before the first request, shutdown after
    the last. `httpx2.ASGITransport` does not, so it is done here -- which is
    the whole point, since the bug this file exists for was a lifespan that
    never ran.
    """

    def __init__(self, app):
        self.app = app
        self._receive = None
        self._sent = []

    async def __aenter__(self):
        import asyncio

        self.events = asyncio.Queue()
        self.started = asyncio.Event()

        async def receive():
            return await self.events.get()

        async def send(message):
            self._sent.append(message)
            if message['type'] in {'lifespan.startup.complete', 'lifespan.startup.failed'}:
                self.started.set()

        self._task = asyncio.create_task(
            self.app({'type': 'lifespan', 'asgi': {'version': '3.0'}}, receive, send)
        )
        await self.events.put({'type': 'lifespan.startup'})
        await asyncio.wait_for(self.started.wait(), timeout=10)
        return self

    async def __aexit__(self, *exc):
        import asyncio

        await self.events.put({'type': 'lifespan.shutdown'})
        with __import__('contextlib').suppress(Exception):
            await asyncio.wait_for(self._task, timeout=10)

    @property
    def startup_failed(self):
        return any(m['type'] == 'lifespan.startup.failed' for m in self._sent)


def _application():
    """The served application, built the way template/asgi.py builds it."""
    import importlib

    import template.asgi

    importlib.reload(template.asgi)
    return template.asgi.application


async def _connect(app, url):
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    http_client = httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url='http://mcp.internal'
    )
    async with http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(*streams[:2]) as session:
                await session.initialize()
                yield session


@pytest.mark.asyncio
async def test_a_real_client_completes_the_handshake_and_lists_tools():
    """The test that would have caught it.

    A handshake, then a tool listing, over the transport an actual MCP client
    uses. Before the lifespan fix this failed at `initialize` with "Task group
    is not initialized".
    """
    app = _application()

    async with _LifespanApp(app) as driver:
        assert not driver.startup_failed, (
            'The MCP session manager did not start. Its task group is what '
            'every request is handled inside, so the endpoint would answer '
            'nothing.'
        )

        async for session in _connect(app, 'http://mcp.internal/mcp'):
            listing = await session.list_tools()

    names = {tool.name for tool in listing.tools}
    assert 'whoami' in names, f'expected the tool surface, got {sorted(names)}'


@pytest.mark.asyncio
async def test_a_tool_call_reaches_a_tool():
    """Without a credential, so the answer is a refusal -- but a refusal that
    came back through the transport, from the tool, is the thing being
    checked. A crash or a hang would look nothing like this."""
    app = _application()

    async with _LifespanApp(app):
        async for session in _connect(app, 'http://mcp.internal/mcp'):
            outcome = await session.call_tool('whoami', {})

    assert outcome.is_error, 'no credential was sent, so this must not succeed'


@pytest.mark.asyncio
async def test_django_still_answers_alongside_it():
    """The router serves two applications. Proving MCP works is half of it."""
    import httpx2

    app = _application()

    async with _LifespanApp(app):
        client = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url='http://mcp.internal'
        )
        async with client:
            response = await client.get('/api/v1/health/')

    assert response.status_code == 200
