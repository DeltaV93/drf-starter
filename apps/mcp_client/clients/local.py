"""This application reaches the MCP server itself.

The transport for everything the connector cannot do: a server on a private
network, a server behind a VPN, a subprocess speaking stdio, a server you are
still writing. Anthropic never sees it -- the traffic is between this process
and the server.

## What this transport has to do that the connector does not

With the connector, Anthropic runs the tool loop: it fetches the server,
offers the tools to the model and feeds results back. Here that loop is ours.

    connect  ->  list the tools  ->  offer them to the model
                                        |
                       model asks for a tool
                                        |
                       call it, feed the result back
                                        |
                       ... until the model stops asking

Which is why this file is longer than `connector.py` while doing the same job
from a caller's point of view -- and why `base.py` exists, so a caller cannot
tell which of the two it got.

## Async, bridged here

The MCP SDK is async and the callers are not: a Celery task, a DRF view, a
management command. The bridge is `async_to_sync` in `_run`, made once here
rather than per server. `arun` is exposed for a caller that is already async
and would otherwise be bridging back and forth for no reason.

## The allow-list is enforced, not just advertised

`allowed_tools` filters what the model is offered *and* is checked again
before a tool actually runs. Two checks for one rule looks redundant until the
model asks for a name it was never offered -- which happens -- and the second
check is the one that means the curated list is a boundary rather than a
suggestion.
"""

from __future__ import annotations

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings

from .base import BaseMCPClient, MCPClientError, MCPResult, ToolCall
from .transports import http_session, stdio_session

# A model that keeps asking for tools would otherwise loop until the process
# is killed. Eight rounds is generous for a real task and cheap to raise.
DEFAULT_MAX_TOOL_ROUNDS = 8


class LocalMCPClient(BaseMCPClient):
    transport = 'local'

    def __init__(self, definition, *, user=None, api=None):
        super().__init__(definition, user=user)
        # Injectable, as in connector.py, so tests can assert on the exact
        # request without reaching the network.
        self._api = api

    # -- the call ---------------------------------------------------------

    def _run(self, messages, *, credential=None, **options):
        return async_to_sync(self.arun)(messages, credential=credential, **options)

    async def aask(self, prompt, *, messages=None, **options) -> MCPResult:
        """`ask`, for a caller that already has an event loop.

        The async twin, not a shortcut past `ask`: it resolves the credential
        and records the call exactly as `ask` does. Without it an async caller
        would reach for `arun` and silently skip both -- which is a call made
        with no credential, and one the audit log never hears about.

        The two hops it wraps touch the database, so they go through
        `sync_to_async` rather than being called from the loop.
        """
        conversation = self._conversation(prompt, messages)
        credential = await sync_to_async(self.credential)()
        result = await self.arun(conversation, credential=credential, **options)
        await sync_to_async(self._record)(result)
        return result

    async def arun(self, messages, *, credential=None, **options) -> MCPResult:
        """Reach the server and return a result. Takes the credential as given.

        `aask` is what a caller normally wants; this is the layer below it,
        and is what `_run` bridges to.
        """
        async with self._connect(credential) as session:
            tools = self._offerable(await session.list_tools())
            return await self._converse(session, list(messages), tools, **options)

    # -- the loop ---------------------------------------------------------

    async def _converse(self, session, messages, tools, **options) -> MCPResult:
        api = self._client()
        model = options.pop('model', None) or self.model
        max_tokens = options.pop('max_tokens', None) or self.max_tokens
        rounds = options.pop('max_tool_rounds', None) or self.max_tool_rounds

        text_parts: list[str] = []
        calls: list[ToolCall] = []
        response = None

        for _ in range(rounds):
            response = self._create(
                api,
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                tools=tools,
                **options,
            )

            requests = []
            for block in getattr(response, 'content', []) or []:
                if getattr(block, 'type', None) == 'text':
                    text_parts.append(getattr(block, 'text', ''))
                elif getattr(block, 'type', None) == 'tool_use':
                    requests.append(block)

            if not requests:
                # The model answered instead of asking for a tool. Done.
                break

            messages.append({'role': 'assistant', 'content': response.content})
            results = []
            for block in requests:
                call, result_block = await self._invoke(session, block, tools)
                calls.append(call)
                results.append(result_block)
            messages.append({'role': 'user', 'content': results})
        else:
            raise MCPClientError(
                f'{self.definition.slug} did not finish within {rounds} tool '
                'rounds. Raise MCP_CLIENT_MAX_TOOL_ROUNDS if the task really '
                'needs more, but a model looping on one tool usually means the '
                'tool is answering with something it cannot use.'
            )

        return MCPResult(text=''.join(text_parts), tool_calls=calls, raw=response)

    async def _invoke(self, session, block, tools):
        """Run one tool and build both records of it.

        Returns the normalised ToolCall for the caller and the result block
        the model needs to see next. A refusal is a *result*, not an
        exception: the model has to be told the tool said no, or it retries
        the same call forever.
        """
        name = getattr(block, 'name', '')
        arguments = getattr(block, 'input', None) or {}

        if name not in {tool['name'] for tool in tools}:
            # The second check. The model was never offered this name.
            content, is_error = f'{name} is not an available tool.', True
        else:
            try:
                outcome = await session.call_tool(name, arguments)
                content = self._readable(outcome)
                is_error = bool(getattr(outcome, 'is_error', False))
            except Exception as exc:
                content, is_error = f'The tool failed: {exc}', True

        return (
            ToolCall(
                server=self.definition.slug,
                tool=name,
                arguments=arguments,
                result=content,
                is_error=is_error,
            ),
            {
                'type': 'tool_result',
                'tool_use_id': getattr(block, 'id', ''),
                'content': content if isinstance(content, str) else str(content),
                'is_error': is_error,
            },
        )

    # -- tools ------------------------------------------------------------

    def list_tools(self) -> list[str]:
        """What this server offers, after the allow-list.

        The connector cannot answer this -- discovery happens on Anthropic's
        side. Here it is a real question with a real answer, which is often
        the reason to choose this transport while developing against a server.
        """
        return [tool['name'] for tool in async_to_sync(self.alist_tools)()]

    async def alist_tools(self) -> list[dict]:
        async with self._connect(self.credential()) as session:
            return self._offerable(await session.list_tools())

    def _offerable(self, listing) -> list[dict]:
        """MCP tool definitions, in the shape the model API wants.

        The two schemas are near-identical -- `inputSchema` becomes
        `input_schema` -- which is exactly why this conversion is easy to skip
        and then wrong in a way that only shows up as the model never calling
        anything.
        """
        allowed = self.definition.allowed_tools
        tools = []
        for tool in getattr(listing, 'tools', []) or []:
            name = getattr(tool, 'name', '')
            if allowed is not None and name not in allowed:
                continue
            tools.append(
                {
                    'name': name,
                    'description': getattr(tool, 'description', '') or '',
                    'input_schema': getattr(tool, 'input_schema', None)
                    or {'type': 'object', 'properties': {}},
                }
            )
        return tools

    @staticmethod
    def _readable(outcome):
        """Flatten a tool result into something a model can read.

        The SDK returns content blocks; the model API wants text. Handing over
        a repr of a pydantic object technically works and produces answers
        that quote field names at the user.
        """
        parts = []
        for block in getattr(outcome, 'content', []) or []:
            text = getattr(block, 'text', None)
            parts.append(text if text is not None else str(block))
        if parts:
            return '\n'.join(parts)

        structured = getattr(outcome, 'structured_content', None)
        return '' if structured is None else str(structured)

    # -- connection -------------------------------------------------------

    def _connect(self, credential):
        options = self.definition.options or {}
        command = options.get('command')

        if command:
            return stdio_session(
                command,
                args=options.get('args'),
                env=options.get('env'),
                cwd=options.get('cwd'),
            )

        if not self.definition.url:
            raise MCPClientError(
                f'{self.definition.slug} has neither a url nor a command, so '
                'there is nothing to connect to. A local server needs one or '
                'the other in its servers/ module.'
            )

        return http_session(self.definition.url, credential=credential, timeout=self.timeout)

    def _client(self):
        if self._api is None:
            self._api = self._build_anthropic_client()
        return self._api

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise MCPClientError(
                'The anthropic package is not installed. It is in '
                'requirements/base.txt under MCP_CLIENT_ENABLED.'
            ) from exc

        self._api = Anthropic(timeout=self.timeout)
        return self._api

    def _create(self, api, **kwargs):
        """One place to call the model.

        Not the beta endpoint: this transport passes ordinary tool
        definitions, because it runs the loop itself. The connector's beta is
        for handing Anthropic a server to fetch, which is not happening here.
        """
        try:
            return api.messages.create(**kwargs)
        except Exception as exc:
            raise MCPClientError(f'The call to {self.definition.slug} failed: {exc}') from exc

    @property
    def max_tool_rounds(self) -> int:
        return getattr(settings, 'MCP_CLIENT_MAX_TOOL_ROUNDS', DEFAULT_MAX_TOOL_ROUNDS)
