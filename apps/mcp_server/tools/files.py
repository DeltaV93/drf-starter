"""Listing files and handing back a link to one.

There is no tool that returns file *content*. A download goes through the
application's signed, expiring URL -- the same one a browser would get -- so
the bytes never pass through the agent's context, and the link stops working
on the timetable the application already sets.
"""

from __future__ import annotations

from apps.mcp_server.call import call_api
from apps.mcp_server.credentials import require_credential


async def list_files() -> list:
    """List the signed-in user's uploaded files: name, type, size and upload date."""
    return await call_api('GET', '/api/v1/files/', credential=require_credential())


async def get_file_download_url(attachment_id: int) -> dict:
    """Return a time-limited download URL for one of the user's own files.

    Args:
        attachment_id: The file's id, as returned by list_files.
    """
    return await call_api(
        'GET', f'/api/v1/files/{attachment_id}/', credential=require_credential()
    )


TOOLS = [list_files, get_file_download_url]
