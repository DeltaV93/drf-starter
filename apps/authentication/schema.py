"""Teaching drf-spectacular about the mobile bearer credential.

Without this the generator cannot resolve `MobileJWTAuthentication` and drops
it with a warning on *every* view -- and CI runs `spectacular --fail-on-warn`,
so the build fails. The published schema would otherwise document session
cookies as the only way in, while the mobile app is signing in with a token.

drf-spectacular ships an extension for SimpleJWT's own `JWTAuthentication`,
but it is registered against that exact class and does not cover a subclass.

Imported from `AuthConfig.ready`. The app is always installed, which is what
this credential's availability tracks: unlike the OAuth one, it needs no
external service to be configured before it works.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication_token import KEYWORD


class MobileJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.authentication.authentication_token.MobileJWTAuthentication'
    name = 'mobileBearer'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': (
                f'`Authorization: {KEYWORD} <access token>`. Obtain a pair from '
                '`/auth/token/` and renew it at `/auth/token/refresh/` before '
                'the access token expires. Intended for clients with no cookie '
                'jar; a browser should use the session endpoints instead.'
            ),
        }
