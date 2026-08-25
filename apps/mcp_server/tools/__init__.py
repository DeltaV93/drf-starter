"""The tool registry.

One module per domain, each exporting a `TOOLS` list. Adding a tool is adding a
function and naming it here -- not editing a monolith.

Every tool is registered explicitly. There is no "derive tools from the OpenAPI
schema" path on purpose: that would make every endpoint added in future
agent-callable by default, opt-out rather than opt-in. What an agent may do is
a decision someone should have to make, once, in writing.

## What is deliberately absent

The rule is: **if the audit log exists to record it, an agent does not get to
do it.** So there is no tool for subscribing, cancelling or adding a billing
add-on; none for minting or revoking API keys; none for removing a member,
deleting an account, or disabling two-factor.

Those are not oversights and they are not blocked by permissions -- they simply
have no tool. `tests/test_excluded_operations.py` pins the list, so adding one
is a deliberate act that shows up in a diff.
"""

from __future__ import annotations

from . import activity, files, identity, organizations, records

# Order is display order in a client's tool list. Identity first because it is
# what an agent should call to orient itself.
MODULES = (identity, organizations, files, activity, records)


def all_tools() -> list:
    """Every registered tool function, flattened."""
    return [tool for module in MODULES for tool in module.TOOLS]


def tool_names() -> set[str]:
    return {tool.__name__ for tool in all_tools()}
