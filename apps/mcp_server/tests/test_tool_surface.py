"""What is exposed, and what is deliberately not.

The tool list is a security decision, so it is pinned here rather than left to
whatever happens to be in `tools/`. Adding or removing a tool has to change
this file too, which puts the decision in the diff where someone reviews it.
"""

from apps.mcp_server.tools import all_tools, tool_names

# The complete surface. Update deliberately.
EXPECTED = {
    'whoami',
    'list_organizations',
    'get_active_organization',
    'list_organization_members',
    'list_files',
    'get_file_download_url',
    'list_my_activity',
    'update_my_profile',
    'request_data_export',
}

# Operations an agent must not have a tool for.
#
# The rule: if the audit log exists to record it, an agent does not get to do
# it. These are not blocked by a permission check -- they simply have no tool,
# which is a stronger guarantee than a check that could be got wrong.
FORBIDDEN_SUBSTRINGS = (
    'subscribe',
    'cancel_subscription',
    'add_addon',
    'create_api_key',
    'revoke_api_key',
    'remove_member',
    'delete_account',
    'disable_two_factor',
    'transfer_ownership',
)


def test_the_tool_surface_is_exactly_what_is_intended():
    assert tool_names() == EXPECTED, (
        'The tool list changed. If that was deliberate, update EXPECTED -- '
        'and consider whether the new tool is something an agent should be '
        'able to do unattended.'
    )


def test_no_tool_exposes_an_excluded_operation():
    offenders = {
        name
        for name in tool_names()
        for forbidden in FORBIDDEN_SUBSTRINGS
        if forbidden in name
    }

    assert not offenders, (
        f'These tools name an excluded operation: {sorted(offenders)}. '
        'Billing changes, credential minting, member removal, account '
        'deletion and disabling two-factor are out of bounds for an agent.'
    )


def test_every_tool_has_a_description_a_model_can_use():
    """The docstring is the description the model reads when choosing a tool.

    An undescribed tool is one the model will either ignore or misuse, so an
    empty docstring is a bug rather than a style lapse.
    """
    undescribed = [tool.__name__ for tool in all_tools() if not (tool.__doc__ or '').strip()]

    assert not undescribed, f'These tools have no docstring: {undescribed}'


def test_every_tool_is_async():
    """`call_api` is awaited, so a sync tool would return a coroutine object
    to the client rather than a result."""
    import inspect

    sync = [t.__name__ for t in all_tools() if not inspect.iscoroutinefunction(t)]

    assert not sync, f'These tools are not async: {sync}'
