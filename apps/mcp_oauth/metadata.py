"""The protected-resource metadata document, and where it lives.

RFC 9728 is what lets a client that knows only this endpoint's URL discover
which authorization server to talk to. Without it, connecting an MCP client
means someone pasting an issuer URL by hand -- which is the difference between
a server anyone can add and one only its author can configure.

## Where the document is served

RFC 9728 derives the metadata URL from the resource identifier the same way
RFC 8414 does for authorization servers: `/.well-known/oauth-protected-resource`
is inserted *between* the origin and the resource's path, rather than appended.

    resource      https://app.example.test/mcp
    metadata      https://app.example.test/.well-known/oauth-protected-resource/mcp

That ordering looks wrong at a glance and is easy to get backwards, which is
why it is derived here once rather than written out in a setting.

The path-suffixed URL is the canonical one, and the bare
`/.well-known/oauth-protected-resource` is served alongside it because a
resource identifier with no path produces exactly that, and because clients
have been observed to try it first. Both return the same document; there is
one resource.

**Unverified here.** The egress proxy in the environment this was written in
blocks `modelcontextprotocol.io`, so the auth revision MCP currently targets
was not read against this implementation. The RFC 9728 shape below is what is
implemented; confirm the revision before relying on it, and record it in
docs/mcp.md.
"""

from urllib.parse import urlsplit

from django.conf import settings

WELL_KNOWN = '/.well-known/oauth-protected-resource'


def metadata_url() -> str:
    """The absolute URL of this resource server's metadata document."""
    parts = urlsplit(settings.MCP_OAUTH_AUDIENCE)
    origin = f'{parts.scheme}://{parts.netloc}'
    path = parts.path.rstrip('/')
    return f'{origin}{WELL_KNOWN}{path}'


def document() -> dict:
    """What a client reads to find the authorization server.

    Deliberately *not* wrapped in the `api_response` envelope. Every other
    endpoint in this project returns `{status, message, data, errors}`, but
    this document's shape is fixed by RFC 9728 -- a client parsing it expects
    `authorization_servers` at the top level, and an envelope would hide it.
    The exception is confined to this one well-known URL and noted in
    docs/configuration.md so nobody "fixes" it later.
    """
    return {
        'resource': settings.MCP_OAUTH_AUDIENCE,
        'authorization_servers': [settings.MCP_OAUTH_ISSUER],
        'scopes_supported': list(settings.MCP_OAUTH_SCOPES_SUPPORTED),
        # Header only. Accepting a token in a query string would write it into
        # every access log and Referer header between here and the client.
        'bearer_methods_supported': ['header'],
    }
