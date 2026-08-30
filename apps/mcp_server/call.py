"""Calling the application's own API, in process.

Every tool reaches data through here, and it goes through the **whole Django
stack** -- middleware, URL resolution, DRF authentication, permission classes,
throttles, serializers -- by making a real ASGI request that never touches a
socket.

That is the point. The alternative, querying the ORM from a tool, would mean
re-implementing per tool every rule the API already enforces: who owns this
row, does this credential carry write scope, is this organization the caller's,
does this action get audited. That is exactly the code an agent must not slip
past, so it is not duplicated -- it is re-used by construction.

An agent therefore cannot reach anything a user holding the same credential
could not reach over HTTP. Not by convention: there is no other path.
"""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import contextmanager
from typing import Any

from django.core.asgi import get_asgi_application
from django.core.signals import request_finished, request_started
from django.db import close_old_connections

# Built once. Django is already configured by the time this is imported, and
# constructing the handler per call would rebuild the middleware chain on every
# tool invocation.
_django_asgi_app = None


def _app():
    global _django_asgi_app
    if _django_asgi_app is None:
        _django_asgi_app = get_asgi_application()
    return _django_asgi_app


# Sub-requests can overlap: two agents calling tools at once share one process,
# and the signal receivers below are global to it. A depth count means the last
# one out restores them, rather than the first one out restoring them while the
# others are still running.
_nesting_lock = threading.Lock()
_nesting = 0


@contextmanager
def _borrowed_connections():
    """Run a sub-request without letting it manage the database connection.

    Django connects `close_old_connections` to `request_started` and
    `request_finished`, which is right for a request that owns its connection
    and wrong for this one: the caller already has one open, and this is a
    nested call inside it rather than a new lifecycle.

    In production the connection closed mid-flight would be the outer HTTP
    request's. Under a test it is the transaction pytest-django wraps each
    test in: `close_old_connections` reads an autocommit setting that no
    longer matches -- being inside `atomic` is exactly that mismatch -- and
    closes it, so the next query raises "the connection is closed". SQLite
    hides the whole thing, because its backend declines to close an in-memory
    database, which is why this only ever failed against PostgreSQL.

    Django's own test client disconnects the same two receivers for the same
    reason. Doing it here rather than in the tests is deliberate: the tests
    are not the only caller, and they should exercise what production runs.
    """
    global _nesting
    with _nesting_lock:
        if _nesting == 0:
            request_started.disconnect(close_old_connections)
            request_finished.disconnect(close_old_connections)
        _nesting += 1
    try:
        yield
    finally:
        with _nesting_lock:
            _nesting -= 1
            if _nesting == 0:
                request_started.connect(close_old_connections)
                request_finished.connect(close_old_connections)


class ApiError(Exception):
    """A non-2xx answer from the application's own API.

    Carries the status and the parsed envelope so a tool can turn a refusal
    into something an agent can read, rather than a stack trace.
    """

    def __init__(self, status: int, payload: Any):
        self.status = status
        self.payload = payload
        message = ''
        if isinstance(payload, dict):
            message = payload.get('message') or ''
        super().__init__(message or f'The API answered {status}.')


async def call_api(
    method: str,
    path: str,
    *,
    credential: str,
    query: str = '',
    body: dict[str, Any] | None = None,
    host: str = 'mcp.internal',
) -> Any:
    """Make an in-process request and return the envelope's `data`.

    `credential` is the caller's own `Authorization` header, passed through
    unchanged. The MCP server holds no credential of its own -- if it did, a
    tool could act with more authority than whoever called it.
    """
    payload = json.dumps(body).encode() if body is not None else b''

    headers = [
        (b'host', host.encode()),
        (b'accept', b'application/json'),
        (b'authorization', credential.encode()),
    ]
    if body is not None:
        headers.append((b'content-type', b'application/json'))
        headers.append((b'content-length', str(len(payload)).encode()))

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1',
        'method': method.upper(),
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': query.encode(),
        'root_path': '',
        'headers': headers,
        'client': ('127.0.0.1', 0),
        'server': ('mcp.internal', 80),
    }

    delivered = asyncio.Event()

    async def receive():
        """Hand over the body once, then block forever.

        Django's ASGI handler watches `receive` for `http.disconnect` on a
        concurrent task while the view runs. Returning one here -- the obvious
        thing to do when there is nothing left to send -- makes it believe the
        client hung up, so it abandons the response and sends nothing at all:
        no status, no body, no exception. Blocking is what a real server does
        between the body and an actual disconnect.
        """
        if delivered.is_set():
            await asyncio.Event().wait()  # never fires; cancelled with the request
        delivered.set()
        return {'type': 'http.request', 'body': payload, 'more_body': False}

    status = 500
    chunks: list[bytes] = []

    async def send(message):
        nonlocal status
        if message['type'] == 'http.response.start':
            status = message['status']
        elif message['type'] == 'http.response.body':
            chunks.append(message.get('body', b''))

    with _borrowed_connections():
        await _app()(scope, receive, send)

    raw = b''.join(chunks)
    try:
        envelope = json.loads(raw) if raw else None
    except json.JSONDecodeError as exc:
        # An HTML error page, most likely. Do not hand an agent a page of
        # markup and call it a result.
        raise ApiError(
            status, {'message': f'The API answered {status} with a non-JSON body.'}
        ) from exc

    if not 200 <= status < 300:
        raise ApiError(status, envelope)

    return envelope.get('data') if isinstance(envelope, dict) else envelope
