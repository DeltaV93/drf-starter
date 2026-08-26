"""The tool loop this transport has to run itself.

With the connector, Anthropic runs the loop: it offers the tools, receives the
model's request, calls the tool and feeds the result back. Here that is ours,
which is the whole substance of this file.

The cases that need a server misbehaving on cue use a fake session. Everything
else is tested against the project's own MCP server over the real transport --
see test_local_end_to_end.py.
"""

import contextlib

import pytest
from django.test import override_settings

from apps.mcp_client.clients.base import MCPClientError
from apps.mcp_client.clients.local import LocalMCPClient
from apps.mcp_client.registry import ServerDefinition

from .fake_session import FakeSession, ScriptedModel, text, tool, tool_use, turn

DEFINITION = ServerDefinition(
    slug='local-server', label='Local', transport='local', url='http://server.test/mcp'
)


def _client(session, model, definition=DEFINITION):
    """A client wired to a fake session and a scripted model.

    `_connect` is overridden rather than given a production hook: a seam that
    exists only for tests is a seam that can be wrong in production.
    """

    class _Wired(LocalMCPClient):
        def _connect(self, credential):
            @contextlib.asynccontextmanager
            async def opened():
                yield session

            return opened()

    return _Wired(definition, api=model)


# ---------------------------------------------------------------------------
# The loop.
# ---------------------------------------------------------------------------


def test_a_tool_result_is_fed_back_and_the_model_answers():
    """The behaviour this transport exists to provide."""
    session = FakeSession(tools=[tool('search')], results={'search': ('three results', False)})
    model = ScriptedModel(
        turn(tool_use('u1', 'search', {'q': 'kettles'})),
        turn(text('I found three.')),
    )

    result = _client(session, model).ask('find kettles')

    assert session.calls == [('search', {'q': 'kettles'})]
    assert result.text == 'I found three.'
    assert [c.tool for c in result.tool_calls] == ['search']
    assert result.tool_calls[0].result == 'three results'


def test_the_result_reaches_the_model_as_a_tool_result_block():
    """A model that is not shown the result asks for the same tool again."""
    session = FakeSession(tools=[tool('search')], results={'search': ('found it', False)})
    model = ScriptedModel(turn(tool_use('u1', 'search')), turn(text('done')))

    _client(session, model).ask('go')

    second = model.calls[1]['messages'][-1]
    assert second['role'] == 'user'
    assert second['content'][0]['type'] == 'tool_result'
    assert second['content'][0]['tool_use_id'] == 'u1'
    assert 'found it' in second['content'][0]['content']


def test_a_model_that_answers_immediately_calls_nothing():
    session = FakeSession(tools=[tool('search')])
    model = ScriptedModel(turn(text('I already know.')))

    result = _client(session, model).ask('what is it')

    assert session.calls == []
    assert result.text == 'I already know.'
    assert not result.used_tools


def test_several_tools_in_one_turn_all_run():
    session = FakeSession(tools=[tool('a'), tool('b')])
    model = ScriptedModel(
        turn(tool_use('u1', 'a'), tool_use('u2', 'b')), turn(text('both done'))
    )

    result = _client(session, model).ask('go')

    assert [name for name, _ in session.calls] == ['a', 'b']
    assert len(result.tool_calls) == 2


def test_a_model_that_never_stops_is_stopped():
    """Without a bound this loops until the process is killed."""
    session = FakeSession(tools=[tool('search')])
    model = ScriptedModel(turn(tool_use('u1', 'search')))  # repeats forever

    with override_settings(MCP_CLIENT_MAX_TOOL_ROUNDS=3):
        with pytest.raises(MCPClientError, match='3 tool rounds'):
            _client(session, model).ask('go')

    assert len(session.calls) == 3


# ---------------------------------------------------------------------------
# When a tool goes wrong.
# ---------------------------------------------------------------------------


def test_a_failing_tool_becomes_a_result_the_model_can_read():
    """Not an exception. The model has to be told the tool failed, or the turn
    ends with nothing and the caller cannot tell why."""
    session = FakeSession(tools=[tool('search')], raises={'search': RuntimeError('boom')})
    model = ScriptedModel(turn(tool_use('u1', 'search')), turn(text('That did not work.')))

    result = _client(session, model).ask('go')

    assert result.errored_tools
    assert 'boom' in result.tool_calls[0].result
    assert result.text == 'That did not work.'


def test_a_tool_that_refuses_is_marked_rather_than_swallowed():
    session = FakeSession(tools=[tool('search')], results={'search': ('not allowed', True)})
    model = ScriptedModel(turn(tool_use('u1', 'search')), turn(text('ok')))

    result = _client(session, model).ask('go')

    assert [c.tool for c in result.errored_tools] == ['search']


# ---------------------------------------------------------------------------
# The allow-list, twice.
# ---------------------------------------------------------------------------


CURATED = ServerDefinition(
    slug='curated',
    label='Curated',
    transport='local',
    url='http://server.test/mcp',
    allowed_tools=('search',),
)


def test_only_allowed_tools_are_offered_to_the_model():
    session = FakeSession(tools=[tool('search'), tool('delete_everything')])
    model = ScriptedModel(turn(text('nothing to do')))

    _client(session, model, CURATED).ask('go')

    assert [t['name'] for t in model.last['tools']] == ['search']


def test_a_tool_that_was_never_offered_is_refused_at_the_call():
    """The second check, and the one that makes the allow-list a boundary
    rather than a suggestion. A model asking for a name it was not offered is
    a thing that happens."""
    session = FakeSession(tools=[tool('search'), tool('delete_everything')])
    model = ScriptedModel(
        turn(tool_use('u1', 'delete_everything')), turn(text('I could not.'))
    )

    result = _client(session, model, CURATED).ask('go')

    assert session.calls == [], 'the tool must not run'
    assert result.errored_tools
    assert 'not an available tool' in result.tool_calls[0].result


def test_no_allow_list_offers_everything():
    """Guards the tests above: filtering must be about the allow-list."""
    session = FakeSession(tools=[tool('search'), tool('delete_everything')])
    model = ScriptedModel(turn(text('nothing to do')))

    _client(session, model).ask('go')

    assert {t['name'] for t in model.last['tools']} == {'search', 'delete_everything'}


# ---------------------------------------------------------------------------
# Schemas, and the connection.
# ---------------------------------------------------------------------------


def test_the_tool_schema_is_converted_for_the_model_api():
    """MCP says `input_schema`, the model API says `input_schema`, and the
    wire format says `inputSchema`. Getting this wrong shows up only as the
    model never calling anything."""
    schema = {'type': 'object', 'properties': {'q': {'type': 'string'}}}
    session = FakeSession(tools=[tool('search', 'Search things', schema)])
    model = ScriptedModel(turn(text('ok')))

    _client(session, model).ask('go')

    offered = model.last['tools'][0]
    assert offered == {
        'name': 'search',
        'description': 'Search things',
        'input_schema': schema,
    }


def test_listing_tools_works_here_unlike_the_connector():
    session = FakeSession(tools=[tool('search'), tool('fetch')])

    assert _client(session, ScriptedModel(turn(text('')))).list_tools() == [
        'search',
        'fetch',
    ]


def test_a_definition_with_nothing_to_connect_to_says_so():
    client = LocalMCPClient(
        ServerDefinition(slug='nowhere', label='Nowhere', transport='local')
    )

    with pytest.raises(MCPClientError, match='neither a url nor a command'):
        client.ask('go')


def test_a_command_is_preferred_over_a_url():
    """A definition carrying both is a stdio server that also happens to note
    where its HTTP twin lives; launching the subprocess is the explicit
    choice."""
    from apps.mcp_client.clients import transports

    definition = ServerDefinition(
        slug='sub',
        label='Sub',
        transport='local',
        url='http://server.test/mcp',
        options={'command': 'my-server', 'args': ['--stdio']},
    )
    opened = {}

    @contextlib.asynccontextmanager
    async def fake_stdio(command, *, args=None, env=None, cwd=None):
        opened.update(command=command, args=args)
        yield FakeSession(tools=[tool('x')])

    original = transports.stdio_session
    try:
        from apps.mcp_client.clients import local as local_module

        local_module.stdio_session = fake_stdio
        LocalMCPClient(definition, api=ScriptedModel(turn(text('ok')))).ask('go')
    finally:
        local_module.stdio_session = original

    assert opened == {'command': 'my-server', 'args': ['--stdio']}
