"""Serving the application to a test, lifespan and all.

`httpx2.ASGITransport` does not run an app's lifespan, and the MCP session
manager's task group is started by exactly that. So a test that skips it gets
an endpoint which accepts connections and answers every call with "Task group
is not initialized" -- which is the bug this helper exists because of.
"""

import asyncio
import contextlib
import importlib


def build_application():
    """The served application, built the way template/asgi.py builds it."""
    import clearpath.asgi

    importlib.reload(clearpath.asgi)
    return clearpath.asgi.application


@contextlib.asynccontextmanager
async def served_application(app=None):
    """Run an ASGI app's lifespan around a block, as a real server would."""
    app = app or build_application()
    events: asyncio.Queue = asyncio.Queue()
    started = asyncio.Event()
    outcome = {}

    async def receive():
        return await events.get()

    async def send(message):
        if message['type'].startswith('lifespan.startup'):
            outcome['startup'] = message['type']
            started.set()

    task = asyncio.create_task(
        app({'type': 'lifespan', 'asgi': {'version': '3.0'}}, receive, send)
    )
    await events.put({'type': 'lifespan.startup'})
    await asyncio.wait_for(started.wait(), timeout=10)

    if outcome.get('startup') == 'lifespan.startup.failed':
        raise AssertionError(
            'The application refused to start up. With MCP mounted this means '
            'the session manager never ran, and the endpoint would answer '
            'nothing.'
        )

    try:
        yield app
    finally:
        await events.put({'type': 'lifespan.shutdown'})
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, timeout=10)
