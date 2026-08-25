"""A worked example, and the documentation for this directory.

Copy this file, change the slug and the URL, and the server is connectable.
Nothing else has to be touched -- `registry.py` finds it by walking the
package.

Disabled unless `MCP_CLIENT_SERVERS` names it (or is empty, which enables
everything defined). Pointed at a domain reserved for documentation, so an
accidentally-enabled example cannot reach anything real.
"""

from apps.mcp_client.registry import ServerDefinition

SERVER = ServerDefinition(
    slug='example',
    label='Example MCP server',
    url='https://mcp.example.com/mcp',
    # Anthropic fetches the server itself. Use 'local' instead when the server
    # is on a private network, or is a subprocess speaking stdio -- see
    # apps/mcp_client/clients/ for what each transport can do.
    transport='connector',
    description=(
        'A placeholder connection. Copy this file to add a real one; it is '
        'the only documentation this directory needs.'
    ),
    # An allow-list, not because these are the only useful tools, but to show
    # where curation goes. Set None to accept whatever the server offers --
    # and understand that the server can then add a tool at any time and it
    # arrives unreviewed.
    allowed_tools=('search', 'fetch'),
    # A deployment-wide credential. Leave empty and set
    # requires_user_credential when the token belongs to the user instead.
    credential_env='EXAMPLE_MCP_TOKEN',
)
