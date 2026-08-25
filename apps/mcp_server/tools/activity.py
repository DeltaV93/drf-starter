"""The caller's own security activity.

Scoped to the caller by the endpoint itself -- there is no endpoint that
returns everybody's events, and this does not invent one. Staff read the audit
log through the admin, which is authenticated and access-controlled separately.
"""

from __future__ import annotations

from apps.mcp_server.call import call_api
from apps.mcp_server.credentials import require_credential


async def list_my_activity() -> dict:
    """List recent security-relevant events recorded against the signed-in user."""
    return await call_api('GET', '/api/v1/account/activity/', credential=require_credential())


TOOLS = [list_my_activity]
