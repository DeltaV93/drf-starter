"""Anthropic reaches the MCP server for us.

The model calls the server's tools directly; nothing about the server's
traffic passes through this application. That is the appeal — no outbound
plumbing, no async, no subprocess — and also the constraint: the server has to
be reachable from Anthropic's network over HTTPS. A server on a private
network or speaking stdio cannot use this transport, which is what `local.py`
exists for.

## Both halves, always

The connector needs `mcp_servers` **and** a matching `mcp_toolset` entry in
`tools`. Sending `mcp_servers` alone is a validation error, not a request that
quietly does nothing — and the two are linked by name, so a mismatch there
fails the same way. Both are built together in `_request` and pinned by a test,
because "I declared the server but forgot the toolset" is the mistake this API
invites.

## Beta

`mcp-client-2025-11-20`, and Claude API / Claude Platform on AWS only — not
Bedrock, not Vertex. The header is one constant in this file and the provider
check is one method, so a change to either is a one-file problem. That
isolation is the reason this transport is its own module rather than a branch
inside `base.py`.
"""

from __future__ import annotations

from .base import (
    BaseMCPClient,
    MCPClientError,
    MCPResult,
    NotSupported,
    ToolCall,
    UnsupportedProvider,
)

# The beta this API is behind. Expected to change; keeping it here means the
# change is one line in one file.
BETA = 'mcp-client-2025-11-20'

# Providers that can serve the connector. Bedrock and Vertex route to Claude
# but not through the endpoint that fetches an MCP server, so a request built
# here would be rejected by the provider rather than by us -- with an error
# that says nothing about MCP.
SUPPORTED_PROVIDERS = ('anthropic', 'aws')


class ConnectorMCPClient(BaseMCPClient):
    transport = 'connector'

    def __init__(self, definition, *, user=None, api=None):
        super().__init__(definition, user=user)
        # Injectable so tests can assert on the exact request without
        # reaching the network. Production passes nothing.
        self._api = api

    # -- the call ---------------------------------------------------------

    def _run(self, messages, *, credential=None, **options):
        self._check_provider()

        try:
            response = self._client().beta.messages.create(
                **self._request(messages, credential=credential, **options)
            )
        except Exception as exc:
            raise MCPClientError(f'The call to {self.definition.slug} failed: {exc}') from exc

        return self._normalise(response)

    def _request(self, messages, *, credential=None, **options) -> dict:
        """The request body, built in one place.

        Kept separate from `_run` so a test can assert on it directly. The
        thing worth asserting is that `mcp_servers` and `tools` are always
        built together -- see the module docstring.
        """
        server: dict = {
            'type': 'url',
            'name': self.definition.slug,
            'url': self.definition.url,
        }
        if credential:
            server['authorization_token'] = credential
        if self.definition.allowed_tools is not None:
            server['tool_configuration'] = {
                'enabled': True,
                'allowed_tools': list(self.definition.allowed_tools),
            }

        request = {
            'model': options.pop('model', None) or self.model,
            'max_tokens': options.pop('max_tokens', None) or self.max_tokens,
            'betas': [BETA],
            'mcp_servers': [server],
            # The other half. `mcp_server_name` must match the server's `name`
            # above, so both are written from the same slug.
            'tools': [{'type': 'mcp_toolset', 'mcp_server_name': self.definition.slug}],
            'messages': messages,
        }
        request.update(options)
        return request

    # -- the response -----------------------------------------------------

    def _normalise(self, response) -> MCPResult:
        """Flatten the response into the shape every transport returns.

        Tool use and its result arrive as separate blocks, matched by id, and
        a *refused* tool call comes back as an ordinary result block with
        `is_error` set rather than as an exception. Pairing them here is what
        lets a caller ask `result.errored_tools` instead of walking blocks.
        """
        text_parts: list[str] = []
        uses: dict[str, dict] = {}
        results: dict[str, tuple] = {}

        for block in getattr(response, 'content', []) or []:
            kind = getattr(block, 'type', None)
            if kind == 'text':
                text_parts.append(getattr(block, 'text', ''))
            elif kind == 'mcp_tool_use':
                uses[getattr(block, 'id', '')] = {
                    'tool': getattr(block, 'name', ''),
                    'server': getattr(block, 'server_name', '') or self.definition.slug,
                    'arguments': getattr(block, 'input', None) or {},
                }
            elif kind == 'mcp_tool_result':
                results[getattr(block, 'tool_use_id', '')] = (
                    getattr(block, 'content', None),
                    bool(getattr(block, 'is_error', False)),
                )

        calls = []
        for use_id, use in uses.items():
            content, is_error = results.get(use_id, (None, False))
            calls.append(
                ToolCall(
                    server=use['server'],
                    tool=use['tool'],
                    arguments=use['arguments'],
                    result=content,
                    is_error=is_error,
                )
            )

        return MCPResult(text=''.join(text_parts), tool_calls=calls, raw=response)

    def list_tools(self):
        raise NotSupported(
            'The connector does not expose a tool listing: Anthropic fetches '
            'the server and the model discovers its tools there, so the list '
            'never reaches this application. Use the local transport if you '
            "need to enumerate tools, or state them in the definition's "
            'allowed_tools.'
        )

    # -- environment ------------------------------------------------------

    def _check_provider(self):
        from django.conf import settings

        provider = getattr(settings, 'MCP_CLIENT_PROVIDER', 'anthropic')
        if provider not in SUPPORTED_PROVIDERS:
            raise UnsupportedProvider(
                f'The MCP connector is not available on {provider!r} -- only '
                f'{" and ".join(SUPPORTED_PROVIDERS)}. Give this server '
                "transport='local' in its servers/ module to reach it from "
                'here instead.'
            )

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
