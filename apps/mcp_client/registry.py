"""Which MCP servers this deployment may talk to.

One file per connection under `servers/`, and a setting that picks which of
them are live. Adding a server is adding a module; removing one is deleting a
module or dropping its slug from `MCP_CLIENT_SERVERS`. There is no table of
URLs to keep in step with the code, and no way for a server to be reachable
without a file in the repository describing it -- which is the property that
makes the set auditable in a diff.

Discovery imports every module under `servers/` and collects each `SERVER`.
Modules starting with an underscore are skipped, so a shared helper can live
alongside the definitions.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from functools import lru_cache

from django.conf import settings


class UnknownServer(LookupError):
    """No such slug, or it is defined but not enabled here."""


@dataclass(frozen=True)
class ServerDefinition:
    """Everything the client needs to reach one MCP server.

    Frozen, and built at import time from a module rather than from a row: a
    connection that appears without a code change is a connection nobody
    reviewed.
    """

    slug: str
    label: str
    # Where the server lives. Required for the connector transport, which
    # gives the URL to Anthropic to fetch; unused by the local transport when
    # it launches a subprocess instead.
    url: str = ''
    # 'connector' -- Anthropic reaches the server directly.
    # 'local'     -- this application reaches it (private network, or stdio).
    # The choice is per server rather than global: a server behind a VPC is
    # simply not reachable from Anthropic's side, whatever the deployment
    # prefers in general.
    transport: str = 'connector'
    description: str = ''
    # The curated surface. None means "whatever the server offers", which is a
    # decision to take deliberately -- a server can add a tool at any time and
    # an allow-list is the only thing that stops it arriving unreviewed.
    allowed_tools: tuple[str, ...] | None = None
    # A deployment-wide credential, read from this environment variable. Left
    # empty when the credential belongs to the user rather than the
    # deployment.
    credential_env: str = ''
    # Whether a per-user credential is required before this server can be
    # used at all. When true and the user has not connected it, the client
    # refuses rather than falling back to the deployment credential -- which
    # would let one user act with another's authority.
    requires_user_credential: bool = False
    # Free-form, for a transport that needs something the others do not.
    options: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.transport == 'connector' and not self.url:
            raise ValueError(
                f'{self.slug}: the connector transport needs a url -- '
                'Anthropic fetches the server itself.'
            )


def _definitions() -> dict[str, ServerDefinition]:
    """Every server defined in `servers/`, enabled or not."""
    from . import servers

    found = {}
    for module in pkgutil.iter_modules(servers.__path__):
        if module.name.startswith('_'):
            continue
        definition = getattr(
            importlib.import_module(f'{servers.__name__}.{module.name}'),
            'SERVER',
            None,
        )
        if definition is None:
            continue
        if definition.slug in found:
            raise ValueError(
                f'Two server modules both define the slug {definition.slug!r}. '
                'A slug is how a stored connection finds its definition, so it '
                'has to be unique.'
            )
        found[definition.slug] = definition
    return found


@lru_cache(maxsize=1)
def _enabled() -> dict[str, ServerDefinition]:
    defined = _definitions()
    allowed = list(getattr(settings, 'MCP_CLIENT_SERVERS', []) or [])

    if not allowed:
        # Empty means "everything defined". The set is already bounded by what
        # is in the repository, so this is not an open door -- it is the
        # difference between listing the modules twice and listing them once.
        return defined

    unknown = [slug for slug in allowed if slug not in defined]
    if unknown:
        raise ValueError(
            f'MCP_CLIENT_SERVERS names servers with no module under '
            f'apps/mcp_client/servers/: {", ".join(sorted(unknown))}. '
            'A typo here would otherwise silently disable a connection.'
        )
    return {slug: defined[slug] for slug in allowed}


def reset() -> None:
    """Drop the cached registry. For tests, and after a settings change."""
    _enabled.cache_clear()


def all_servers() -> list[ServerDefinition]:
    return list(_enabled().values())


def slugs() -> list[str]:
    return list(_enabled())


def get(slug: str) -> ServerDefinition:
    try:
        return _enabled()[slug]
    except KeyError:
        raise UnknownServer(
            f'{slug!r} is not an enabled MCP server. Enabled: '
            f'{", ".join(slugs()) or "(none)"}.'
        ) from None
