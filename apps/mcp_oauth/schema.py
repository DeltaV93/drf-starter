"""Teaching drf-spectacular about the bearer credential.

Without this the generator cannot resolve `BearerTokenAuthentication` and
drops it with a warning on *every* view -- and CI runs
`spectacular --fail-on-warn`, so the build fails. The published schema would
otherwise document session cookies as the only way in, while an MCP client is
connecting with a token.

Imported from `apps.mcp_oauth.apps.McpOauthConfig.ready`, which only runs when
the app is installed, so nothing here loads with the flag off.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication import KEYWORD


class BearerTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.mcp_oauth.authentication.BearerTokenAuthentication'
    name = 'oauth2Bearer'

    def get_security_definition(self, auto_schema):
        # Declared as `http bearer` rather than as an `oauth2` flow. An oauth2
        # definition has to name the authorization and token endpoints, and
        # this application knows only its authorization server's *issuer* --
        # the endpoints live in that server's own metadata, which is not
        # fetched at schema-generation time. Writing plausible-looking URLs
        # into the published schema would be a guess presented as a fact.
        # Pointing at discovery instead is the honest version.
        from .metadata import metadata_url

        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': (
                f'`Authorization: {KEYWORD} <token>`. This application validates '
                'tokens and never issues them. Fetch '
                f'`{metadata_url()}` to discover which authorization server to '
                'obtain one from.'
            ),
        }
