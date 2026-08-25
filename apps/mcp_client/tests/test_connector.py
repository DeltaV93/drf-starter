"""The request the connector builds, and what it makes of the answer.

The request body is the part worth pinning hardest. The connector API needs
`mcp_servers` **and** a matching `mcp_toolset` in `tools`; sending one without
the other is a validation error, not a request that quietly does nothing. That
is a mistake this shape of API invites, so it is asserted rather than trusted.

Nothing here reaches the network: the SDK is injected.
"""

import pytest
from django.test import override_settings

from apps.mcp_client.clients.base import MCPClientError, NotSupported, UnsupportedProvider
from apps.mcp_client.clients.connector import BETA, ConnectorMCPClient
from apps.mcp_client.registry import ServerDefinition

from .fakes import (
    FakeAnthropic,
    block_response,
    text_block,
    tool_result_block,
    tool_use_block,
)

DEFINITION = ServerDefinition(
    slug='example',
    label='Example',
    url='https://mcp.example.com/mcp',
    allowed_tools=('search', 'fetch'),
)

OPEN_DEFINITION = ServerDefinition(
    slug='open', label='Open', url='https://open.example.com/mcp', allowed_tools=None
)


def _client(definition=DEFINITION, api=None, **kwargs):
    return ConnectorMCPClient(definition, api=api or FakeAnthropic(), **kwargs)


# ---------------------------------------------------------------------------
# The request.
# ---------------------------------------------------------------------------


def test_both_halves_of_the_connector_are_always_sent():
    """`mcp_servers` alone is a validation error.

    The two are linked by name, so this also checks they agree -- declaring a
    server as one name and the toolset as another fails the same way, and is
    the easier mistake to make.
    """
    api = FakeAnthropic()
    _client(api=api).ask('hello')

    sent = api.messages.last
    assert sent['mcp_servers'][0]['name'] == 'example'
    assert sent['tools'] == [{'type': 'mcp_toolset', 'mcp_server_name': 'example'}]
    assert sent['mcp_servers'][0]['url'] == 'https://mcp.example.com/mcp'
    assert sent['mcp_servers'][0]['type'] == 'url'


def test_the_beta_header_is_sent():
    api = FakeAnthropic()
    _client(api=api).ask('hello')

    assert api.messages.last['betas'] == [BETA]


def test_the_allow_list_is_passed_to_the_server():
    """Curation has to reach the request or it is a comment.

    A server can add a tool at any time; the allow-list is the only thing that
    stops it arriving unreviewed.
    """
    api = FakeAnthropic()
    _client(api=api).ask('hello')

    config = api.messages.last['mcp_servers'][0]['tool_configuration']
    assert config == {'enabled': True, 'allowed_tools': ['search', 'fetch']}


def test_no_allow_list_sends_no_tool_configuration():
    """`allowed_tools=None` means "whatever the server offers", and sending an
    empty allow-list instead would mean the opposite."""
    api = FakeAnthropic()
    _client(OPEN_DEFINITION, api=api).ask('hello')

    assert 'tool_configuration' not in api.messages.last['mcp_servers'][0]


def test_a_credential_is_sent_as_the_servers_authorization_token():
    api = FakeAnthropic()
    _client(api=api)._run([{'role': 'user', 'content': 'hi'}], credential='tok-123')

    assert api.messages.last['mcp_servers'][0]['authorization_token'] == 'tok-123'


def test_no_credential_sends_no_authorization_token():
    """A public server needs none, and an empty string is not the same as
    absent -- it would be sent and rejected."""
    api = FakeAnthropic()
    _client(api=api)._run([{'role': 'user', 'content': 'hi'}], credential=None)

    assert 'authorization_token' not in api.messages.last['mcp_servers'][0]


def test_the_prompt_is_appended_to_an_existing_conversation():
    api = FakeAnthropic()
    _client(api=api).ask('and then?', messages=[{'role': 'user', 'content': 'first'}])

    assert [m['content'] for m in api.messages.last['messages']] == ['first', 'and then?']


def test_nothing_to_send_is_refused_rather_than_sent_empty():
    api = FakeAnthropic()
    with pytest.raises(MCPClientError):
        _client(api=api).ask('')

    assert not api.messages.calls


def test_the_model_must_be_configured():
    """No default in code: a model ID baked into a template ages quietly, and
    keeps working while better models ship."""
    with override_settings(MCP_CLIENT_MODEL=''):
        with pytest.raises(MCPClientError, match='MCP_CLIENT_MODEL'):
            _client().ask('hello')


def test_options_reach_the_request():
    api = FakeAnthropic()
    _client(api=api).ask('hello', max_tokens=99, temperature=0.2)

    assert api.messages.last['max_tokens'] == 99
    assert api.messages.last['temperature'] == 0.2


# ---------------------------------------------------------------------------
# The response.
# ---------------------------------------------------------------------------


def test_text_and_tool_calls_are_flattened():
    api = FakeAnthropic(
        response=block_response(
            text_block('Looking that up. '),
            tool_use_block('u1', 'search', {'q': 'kettles'}),
            tool_result_block('u1', [{'type': 'text', 'text': 'three results'}]),
            text_block('Found three.'),
        )
    )

    result = _client(api=api).ask('find kettles')

    assert result.text == 'Looking that up. Found three.'
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert (call.tool, call.arguments) == ('search', {'q': 'kettles'})
    assert call.result == [{'type': 'text', 'text': 'three results'}]
    assert not call.is_error


def test_a_refused_tool_call_is_visible_rather_than_silent():
    """A refusal arrives as an ordinary result block, not an exception.

    A caller that never looks would read "the server said no" as a successful
    turn, which is why `errored_tools` exists.
    """
    api = FakeAnthropic(
        response=block_response(
            tool_use_block('u1', 'fetch', {'url': 'x'}),
            tool_result_block('u1', 'not allowed', is_error=True),
            text_block('I could not fetch that.'),
        )
    )

    result = _client(api=api).ask('fetch it')

    assert result.used_tools
    assert [c.tool for c in result.errored_tools] == ['fetch']


def test_a_tool_use_with_no_matching_result_still_appears():
    """A truncated turn should not make a tool call vanish from the record."""
    api = FakeAnthropic(response=block_response(tool_use_block('u1', 'search', {})))

    result = _client(api=api).ask('go')

    assert [c.tool for c in result.tool_calls] == ['search']
    assert result.tool_calls[0].result is None


def test_an_sdk_failure_becomes_one_error_type():
    api = FakeAnthropic(error=RuntimeError('connection reset'))

    with pytest.raises(MCPClientError, match='connection reset'):
        _client(api=api).ask('hello')


# ---------------------------------------------------------------------------
# The environment.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('provider', ['bedrock', 'vertex'])
def test_an_unsupported_provider_fails_with_a_useful_message(provider):
    """Bedrock and Vertex route to Claude but not through the endpoint that
    fetches an MCP server. Without this check the provider rejects the request
    with an error that says nothing about MCP."""
    api = FakeAnthropic()
    with override_settings(MCP_CLIENT_PROVIDER=provider):
        with pytest.raises(UnsupportedProvider, match="transport='local'"):
            _client(api=api).ask('hello')

    assert not api.messages.calls


@pytest.mark.parametrize('provider', ['anthropic', 'aws'])
def test_the_supported_providers_are_allowed(provider):
    """Guards the test above: the refusal must be about the provider."""
    api = FakeAnthropic()
    with override_settings(MCP_CLIENT_PROVIDER=provider):
        _client(api=api).ask('hello')

    assert api.messages.calls


def test_listing_tools_says_why_it_cannot():
    """Tool discovery happens on Anthropic's side and never reaches us. An
    empty list would be a lie; an unhelpful error would send someone reading
    the SDK."""
    with pytest.raises(NotSupported, match='local transport'):
        _client().list_tools()
