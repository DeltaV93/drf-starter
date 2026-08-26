"""The local transport against this project's own MCP server.

Both halves of the MCP work in one process, so the client can be pointed at
the server and the whole path exercised for real: a genuine handshake, a
genuine tool listing, genuine schema conversion, a genuine tool call reaching
a genuine Django view. Only the model is faked, because only the model needs
an API key.

This is the test that would have caught the two bugs found while writing this
transport -- an unrun lifespan and a Host allow-list defaulting to
`127.0.0.1` -- both of which left an endpoint that mounted perfectly and
answered nothing.
"""

import contextlib

import pytest
from asgiref.sync import sync_to_async
from django.conf import settings

from apps.mcp_client.clients.local import LocalMCPClient
from apps.mcp_client.registry import ServerDefinition

from .fake_session import ScriptedModel, text, tool_use, turn

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not settings.MCP_SERVER_ENABLED, reason='the MCP server is switched off'
    ),
    pytest.mark.skipif(
        not settings.API_KEYS_ENABLED,
        reason='the tests need a concrete credential; the server needs none',
    ),
]

URL = 'http://mcp.internal/mcp'


def _ours(**overrides):
    return ServerDefinition(
        slug='self', label='This application', transport='local', url=URL, **overrides
    )


class _AgainstOurselves(LocalMCPClient):
    """Points the local transport at this process's own MCP endpoint.

    `_connect` is overridden to hand back a session over an in-process ASGI
    transport instead of a socket. Everything below that -- handshake, tool
    listing, tool calls -- is the real code on both sides.
    """

    def __init__(self, definition, *, credential=None, **kwargs):
        super().__init__(definition, **kwargs)
        self._credential = credential

    def credential(self):
        return self._credential

    def _connect(self, credential):
        import httpx2
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        from apps.mcp_server.tests.helpers import served_application

        headers = {'Authorization': credential} if credential else {}

        @contextlib.asynccontextmanager
        async def opened():
            async with served_application() as app:
                http_client = httpx2.AsyncClient(
                    transport=httpx2.ASGITransport(app=app),
                    base_url='http://mcp.internal',
                    headers=headers,
                )
                async with http_client:
                    async with streamable_http_client(URL, http_client=http_client) as streams:
                        async with ClientSession(*streams[:2]) as session:
                            await session.initialize()
                            yield session

        return opened()


async def _key_for(user):
    from apps.api_keys.models import APIKey, generate_key

    full_key, prefix, hashed = generate_key()
    await sync_to_async(APIKey.objects.create)(
        user=user,
        name='local-transport-test',
        scope=APIKey.Scope.READ,
        prefix=prefix,
        hashed_secret=hashed,
    )
    return f'Api-Key {full_key}'


@pytest.mark.asyncio
async def test_the_client_lists_this_applications_own_tools():
    client = _AgainstOurselves(_ours())

    tools = await client.alist_tools()

    names = {tool['name'] for tool in tools}
    assert 'whoami' in names
    # The conversion, on real definitions rather than a fake's.
    assert all({'name', 'description', 'input_schema'} == set(t) for t in tools)


@pytest.mark.asyncio
async def test_the_allow_list_filters_real_tools():
    client = _AgainstOurselves(_ours(allowed_tools=('whoami',)))

    assert [tool['name'] for tool in await client.alist_tools()] == ['whoami']


@pytest.mark.asyncio
async def test_a_tool_call_reaches_django_and_comes_back_with_real_data(
    django_user_model,
):
    """The whole path: model asks for a tool, the transport calls it, the MCP
    server makes an in-process Django request, the row comes back, the result
    is fed to the model."""
    user = await sync_to_async(django_user_model.objects.create_user)(
        username='ada', email='ada@example.com', password='hunter2hunter2'
    )
    credential = await _key_for(user)

    client = _AgainstOurselves(
        _ours(allowed_tools=('whoami',)),
        credential=credential,
        api=ScriptedModel(turn(tool_use('u1', 'whoami')), turn(text('You are Ada.'))),
    )

    result = await client.aask('who am I?')

    assert result.text == 'You are Ada.'
    assert [c.tool for c in result.tool_calls] == ['whoami']
    assert not result.errored_tools, result.tool_calls[0].result
    assert 'ada@example.com' in str(result.tool_calls[0].result)


@pytest.mark.asyncio
async def test_without_a_credential_the_tool_refuses_rather_than_answering():
    """Guards the test above. The MCP server holds no credential of its own,
    so an uncredentialed call must come back as a refusal -- not as somebody
    else's data, and not as a crash."""
    client = _AgainstOurselves(
        _ours(allowed_tools=('whoami',)),
        api=ScriptedModel(turn(tool_use('u1', 'whoami')), turn(text('I cannot tell.'))),
    )

    result = await client.aask('who am I?')

    assert result.errored_tools
