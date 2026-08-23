"""Teaching drf-spectacular about the API-key credential.

Without this the generator cannot resolve `APIKeyAuthentication` and drops it
with a warning, so the published schema documents session cookies as the only
way in -- while the README hands out a curl command that uses a key. The
extension is imported from `apps.api_keys.apps.ApiKeysConfig.ready`, which only
runs when the app is installed, so nothing here loads with the flag off.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication import KEYWORD


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.api_keys.authentication.APIKeyAuthentication'
    name = 'apiKeyAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': KEYWORD.lower(),
            'description': (
                f'`Authorization: {KEYWORD} <prefix>.<secret>`. The full key is shown '
                'once, when it is created, and is not retrievable afterwards.'
            ),
        }
