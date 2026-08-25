"""Who the caller is.

The tool an agent should reach for first: it turns an opaque credential into a
name, an email and a role, so everything after it can be phrased in terms of
the actual person rather than "the authenticated user".
"""

from __future__ import annotations

from apps.mcp_server.call import call_api
from apps.mcp_server.credentials import require_credential


async def whoami() -> dict:
    """Return the signed-in user's profile: name, email, role, verification status."""
    return await call_api('GET', '/api/v1/users/me/', credential=require_credential())


TOOLS = [whoami]
