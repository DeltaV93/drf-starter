"""Reading the caller's teams.

Read-only by design. Membership changes -- removing someone, changing a role,
transferring ownership -- are audited events, so they have no tool here.

Every call is scoped by the API itself: `/organizations/` returns the caller's
own memberships and nothing else, because that is what the endpoint does. This
module adds no filtering of its own, and must not, or there would be two places
where scoping could be got wrong.
"""

from __future__ import annotations

from apps.mcp_server.call import call_api
from apps.mcp_server.credentials import require_credential


async def list_organizations() -> list:
    """List the organizations the signed-in user belongs to, with their role in each."""
    return await call_api('GET', '/api/v1/organizations/', credential=require_credential())


async def get_active_organization() -> dict:
    """Return the organization the current session is acting for, or null if there is none."""
    return await call_api(
        'GET', '/api/v1/organizations/active/', credential=require_credential()
    )


async def list_organization_members() -> list:
    """List the members of the active organization, with their roles."""
    return await call_api(
        'GET', '/api/v1/organizations/current/members/', credential=require_credential()
    )


TOOLS = [list_organizations, get_active_organization, list_organization_members]
