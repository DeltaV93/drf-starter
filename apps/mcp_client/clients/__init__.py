"""Transports. One base class holding the shared behaviour, one file each.

`base.py` owns everything that is the same whichever way the server is
reached: resolving the credential, refusing when there is none, the result
shape, the audit call, the error type. A transport implements `_run` and
nothing else.

`connector.py` -- Anthropic reaches the server over HTTPS on our behalf.
`local.py`     -- this application reaches it (private network, or stdio).

Picking one is per server, in its `servers/` module, not a global setting: a
server behind a VPC is simply not reachable from Anthropic's side whatever a
deployment would prefer.
"""

from .base import BaseMCPClient, MCPClientError, MCPResult, ToolCall, UnsupportedProvider

__all__ = [
    'BaseMCPClient',
    'MCPClientError',
    'MCPResult',
    'ToolCall',
    'UnsupportedProvider',
]
