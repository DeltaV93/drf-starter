"""The writes.

Everything above this module reads. This is where an agent changes something,
and it is deliberately the smallest surface that is still useful: update your
own profile, and ask for a copy of your own data.

## Why these two and not more

The rule the whole tool surface follows: **if the audit log exists to record
it, an agent does not get to do it.** That rules out billing changes, minting
or revoking credentials, removing members, deleting an account and disabling
two-factor — actions where an agent misreading an instruction costs money,
access or data that cannot be recovered by asking again.

Updating a display name is recoverable by updating it back. Requesting an
export sends a link to the account's own address, so the worst case is an email
the owner did not ask for.

## Scope

Both go through the application's API, which refuses a write to a `read`-scoped
credential. That check lives in `apps/api_keys/permissions.py` and is not
repeated here — one place to get right, and it is already got right.

This module is the natural home for a template adopter's own writes. Add them
here, keep them recoverable, and add the excluded ones to
`tests/test_excluded_operations.py` if you decide otherwise.
"""

from __future__ import annotations

from apps.mcp_server.call import call_api
from apps.mcp_server.credentials import require_credential


async def update_my_profile(
    first_name: str | None = None,
    last_name: str | None = None,
    phone_number: str | None = None,
) -> dict:
    """Update the signed-in user's own profile. Only the fields you pass change.

    Args:
        first_name: New given name, or omit to leave unchanged.
        last_name: New family name, or omit to leave unchanged.
        phone_number: New phone number, or omit to leave unchanged.
    """
    fields = {
        'first_name': first_name,
        'last_name': last_name,
        'phone_number': phone_number,
    }
    body = {key: value for key, value in fields.items() if value is not None}

    if not body:
        raise ValueError('Pass at least one field to change.')

    return await call_api(
        'PATCH', '/api/v1/users/me/', credential=require_credential(), body=body
    )


async def request_data_export() -> dict:
    """Request a copy of the signed-in user's data.

    The download link is emailed to the account's own address rather than
    returned here — holding a credential is not the same as being able to
    receive the account's mail.
    """
    return await call_api(
        'POST', '/api/v1/account/export/', credential=require_credential(), body={}
    )


TOOLS = [update_my_profile, request_data_export]
