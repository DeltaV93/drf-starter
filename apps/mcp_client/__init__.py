"""Calling *out* to MCP servers.

The mirror of apps/mcp_server. That app makes this application callable by an
agent; this one lets the application be the agent -- reaching other people's
MCP servers to answer a question or do a job.

The entry point is `client_for(slug, user=...)`. Everything else is a detail
of which transport that slug uses.
"""

from .factory import client_for

__all__ = ['client_for']
