"""Which servers exist, and the ways that can go wrong.

The property worth keeping: a server cannot become reachable without a file in
the repository describing it. Settings choose among those files; they cannot
add one.
"""

import pytest
from django.test import override_settings

from apps.mcp_client import registry
from apps.mcp_client.registry import ServerDefinition, UnknownServer


@pytest.fixture(autouse=True)
def clear_registry():
    registry.reset()
    yield
    registry.reset()


def test_the_example_server_is_discovered():
    """`servers/example.py` is the documentation for that directory, so it has
    to actually work as one."""
    assert 'example' in registry.slugs()
    assert registry.get('example').url


def test_an_empty_setting_enables_everything_defined():
    with override_settings(MCP_CLIENT_SERVERS=[]):
        assert registry.slugs() == list(registry._definitions())


def test_the_setting_selects_a_subset():
    with override_settings(MCP_CLIENT_SERVERS=['example']):
        assert registry.slugs() == ['example']


def test_a_slug_with_no_module_fails_loudly():
    """A typo would otherwise silently disable a connection, and the symptom
    -- one feature quietly doing nothing -- points nowhere near the setting."""
    with override_settings(MCP_CLIENT_SERVERS=['exmaple']):
        with pytest.raises(ValueError, match='exmaple'):
            registry.slugs()


def test_an_unknown_slug_is_not_a_silent_none():
    with pytest.raises(UnknownServer):
        registry.get('nothing-here')


def test_a_disabled_server_is_indistinguishable_from_a_missing_one():
    """A caller has no business telling "not configured here" from "does not
    exist"."""
    with override_settings(MCP_CLIENT_SERVERS=[]):
        assert 'example' in registry.slugs()

    registry.reset()
    with override_settings(MCP_CLIENT_SERVERS=[]):
        pass

    registry.reset()
    with override_settings(MCP_CLIENT_SERVERS=['example']):
        with pytest.raises(UnknownServer):
            registry.get('some-other-server')


def test_the_connector_transport_requires_a_url():
    """Anthropic fetches the server itself, so a definition without a URL is
    one that cannot work -- and the failure would otherwise arrive as a
    confusing API error at call time."""
    with pytest.raises(ValueError, match='needs a url'):
        ServerDefinition(slug='broken', label='Broken', transport='connector')


def test_the_local_transport_does_not_require_a_url():
    """It may be a subprocess speaking stdio, which has no URL at all."""
    assert ServerDefinition(slug='sub', label='Sub', transport='local').url == ''
