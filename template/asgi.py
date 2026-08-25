"""ASGI config — what the container serves.

`gunicorn template.asgi:application -k uvicorn.workers.UvicornWorker`.

Two applications live behind one port. Requests under `MCP_MOUNT_PATH` go to
the MCP endpoint; everything else goes to Django. The MCP transport is
ASGI-only, which is why the whole application is served this way.

**Dispatch happens before Django.** So MCP traffic never traverses Django's
middleware, and the SPA catch-all cannot swallow `/mcp` — the URLconf is never
consulted for those paths. Tools still reach data through the full Django
stack: `apps/mcp_server/call.py` makes a real in-process request that goes
through every middleware, permission class and throttle.

With `MCP_SERVER_ENABLED` off there is no router at all — `application` is
Django's ASGI app and nothing about serving differs from before MCP existed.

https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'template.settings')

django_application = get_asgi_application()


def _with_mcp(django_app):
    """Route MCP paths to the MCP endpoint, everything else to Django."""
    # Imported after get_asgi_application() so the app registry is ready --
    # apps.mcp_server reaches Django models through the API, but its module
    # import chain still touches settings and installed apps.
    from django.conf import settings

    from apps.mcp_server.asgi import build_mcp_app

    mcp_app = build_mcp_app()
    mount = settings.MCP_MOUNT_PATH.rstrip('/')

    async def router(scope, receive, send):
        if scope['type'] in {'http', 'websocket'}:
            path = scope.get('path', '')
            # Exactly the mount, or a path beneath it. A prefix test alone
            # would also capture `/mcp-something`, which is a different route.
            if path == mount or path.startswith(f'{mount}/'):
                await mcp_app(scope, receive, send)
                return
        await django_app(scope, receive, send)

    return router


def _build():
    from django.conf import settings

    if not getattr(settings, 'MCP_SERVER_ENABLED', False):
        return django_application
    return _with_mcp(django_application)


application = _build()
