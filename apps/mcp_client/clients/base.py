"""Everything a transport does not have to think about.

The split is deliberate and it is the whole design: a transport answers *how a
server is reached*, and this class answers everything else -- which credential
is used, what happens when there is none, what a caller gets back, what is
recorded. Two transports that disagree about any of those would be two
integrations wearing one name.

## The credential rule

A per-user credential wins over the deployment-wide one, and a server marked
`requires_user_credential` refuses rather than falling back. That refusal is
the point: falling back would let a user who has authorised nothing act with
the deployment's authority -- and on an outbound call, with whatever authority
*another* user's connection had. Same confused-deputy shape the MCP server
side avoids by holding no credential of its own.

## Sync, deliberately

The call surface is synchronous, because the callers are: a Celery task, a DRF
view, a management command. The connector transport is natively sync. The
local transport is natively async and bridges *inside* `_run`, so the decision
is made once here rather than per server -- which is what the plan called for
and what keeps a caller from having to know which transport it got.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from django.conf import settings
from django.utils import timezone

from apps.core.audit import AuditAction, audit

from ..registry import ServerDefinition


class MCPClientError(Exception):
    """Anything that stopped the call from producing a result."""


class MissingCredential(MCPClientError):
    """No usable credential for this server and this user."""


class UnsupportedProvider(MCPClientError):
    """This transport cannot run against the configured provider."""


class NotSupported(MCPClientError):
    """A transport was asked for something it genuinely cannot do."""


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation, normalised across transports."""

    server: str
    tool: str
    arguments: dict = field(default_factory=dict)
    result: Any = None
    is_error: bool = False


@dataclass(frozen=True)
class MCPResult:
    """What a caller gets, whichever transport produced it.

    `raw` is kept so a caller that needs a transport-specific detail can reach
    it without this class growing a field for every one -- but reaching for it
    is the point at which the code stops being transport-agnostic, so it is
    worth noticing when you do.
    """

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None

    @property
    def used_tools(self) -> bool:
        return bool(self.tool_calls)

    @property
    def errored_tools(self) -> list[ToolCall]:
        """Tool calls the server refused or failed.

        A refusal comes back as an ordinary result block, not an exception, so
        a caller that never looks at this will treat "the server said no" as a
        successful turn.
        """
        return [call for call in self.tool_calls if call.is_error]


class BaseMCPClient(ABC):
    transport: ClassVar[str]

    def __init__(self, definition: ServerDefinition, *, user=None):
        self.definition = definition
        self.user = user

    # -- the call ---------------------------------------------------------

    def ask(self, prompt: str, *, messages: list[dict] | None = None, **options):
        """Put a prompt to the model with this server's tools available.

        `messages` continues an existing conversation; `prompt` is appended to
        it. Passing only `prompt` is the common case.
        """
        conversation = self._conversation(prompt, messages)
        result = self._run(conversation, credential=self.credential(), **options)
        self._record(result)
        return result

    @staticmethod
    def _conversation(prompt, messages):
        conversation = list(messages or [])
        if prompt:
            conversation.append({'role': 'user', 'content': prompt})
        if not conversation:
            raise MCPClientError('There is nothing to send: no prompt and no messages.')
        return conversation

    @abstractmethod
    def _run(self, messages: list[dict], *, credential: str | None, **options) -> MCPResult:
        """Reach the server and return a normalised result."""

    def list_tools(self) -> list[str]:
        """The tools this server offers.

        Not every transport can answer this -- see `connector.py`, where tool
        discovery happens on Anthropic's side and never reaches us.
        """
        raise NotSupported(f'The {self.transport} transport cannot list tools before a call.')

    # -- the credential ---------------------------------------------------

    def connection(self):
        """This user's stored authorisation for this server, if any."""
        if self.user is None or not self.user.is_authenticated:
            return None

        from ..models import ConnectedServer

        return ConnectedServer.objects.filter(
            user=self.user, slug=self.definition.slug, enabled=True
        ).first()

    def credential(self) -> str | None:
        """The token this call will use.

        A per-user credential first, then the deployment-wide one -- unless
        the server requires a user credential, in which case there is no
        fallback. See the module docstring for why that refusal matters.
        """
        connection = self.connection()
        if connection is not None and connection.credential:
            return connection.credential

        if self.definition.requires_user_credential:
            raise MissingCredential(
                f'{self.definition.slug} needs your own authorisation before it '
                'can be used. Connect it first.'
            )

        if self.definition.credential_env:
            import os

            from_env = os.environ.get(self.definition.credential_env)
            if from_env:
                return from_env

        # None is legitimate: a public MCP server needs no credential. It is
        # the transport's business whether that is acceptable.
        return None

    # -- bookkeeping ------------------------------------------------------

    def _record(self, result: MCPResult) -> None:
        connection = self.connection()
        if connection is not None:
            # Bypassing save() so a concurrent write to the credential is not
            # clobbered by a timestamp update.
            type(connection).objects.filter(pk=connection.pk).update(
                last_used_at=timezone.now()
            )

        audit(
            AuditAction.MCP_SERVER_CALLED,
            actor=self.user if self.user and self.user.is_authenticated else None,
            target=self.definition.slug,
            transport=self.transport,
            tools_used=[call.tool for call in result.tool_calls],
        )

    # -- helpers for transports -------------------------------------------

    @property
    def model(self) -> str:
        """The model to call.

        No default in code on purpose. A model identifier baked into a
        template ages badly and quietly: it keeps working while newer, better
        models ship, and nobody notices because nothing fails. Making it
        configuration forces the choice to be made by whoever deploys, against
        the model list current at the time.
        """
        model = getattr(settings, 'MCP_CLIENT_MODEL', '')
        if not model:
            raise MCPClientError(
                'MCP_CLIENT_MODEL is not set. Set it to the model ID you want '
                'to call -- see the Anthropic documentation for current IDs.'
            )
        return model

    @property
    def max_tokens(self) -> int:
        return getattr(settings, 'MCP_CLIENT_MAX_TOKENS', 4096)

    @property
    def timeout(self) -> float:
        return getattr(settings, 'MCP_CLIENT_TIMEOUT_SECONDS', 60.0)
