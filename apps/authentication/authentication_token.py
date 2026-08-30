"""Authenticating a request with a bearer token issued to the mobile app.

Registered first in DEFAULT_AUTHENTICATION_CLASSES, alongside
SessionAuthentication rather than instead of it -- the browser keeps using
cookies, and apps/authentication/tests/test_csrf.py still pins that.

## Why this class exists at all, rather than SimpleJWT's own

Two bearer schemes can be live at once in this project. `apps/mcp_oauth`
validates tokens minted by an external authorization server; this one
validates tokens this application minted itself. They arrive on the same
`Authorization: Bearer ...` header and are told apart by nothing but their
contents.

SimpleJWT's `JWTAuthentication` raises `InvalidToken` for anything it cannot
verify. So does `mcp_oauth`'s class. Two authenticators that both raise cannot
be chained in either order: whichever runs first rejects the other's tokens
outright, and DRF stops at the first exception. One of them has to *decline*.

This one declines. It reads the `iss` claim without verifying anything, and if
it is not ours it returns None so the next authenticator gets its turn. Only
once the issuer matches does it verify for real -- and then a bad signature,
a wrong audience or an expired token is a hard failure, exactly as it should
be, because at that point the token was addressed to us.

Reading a claim before checking the signature deserves suspicion, so to be
explicit: the unverified value is used only to choose which authenticator
handles the request. It never reaches an authorization decision. Claiming to
be ours buys an attacker nothing but a strict signature check.
"""

import jwt
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

AUTH_HEADER = 'HTTP_AUTHORIZATION'
KEYWORD = 'Bearer'


class MobileJWTAuthentication(JWTAuthentication):
    """`Authorization: Bearer <token issued by auth/token/>`."""

    def authenticate(self, request):
        if not self._is_ours(request):
            # Either not a bearer token at all, or one minted elsewhere.
            # Declining rather than raising is the whole point of this class.
            return None
        return super().authenticate(request)

    def authenticate_header(self, request):
        """The `WWW-Authenticate` challenge for an unauthenticated request.

        Returning something here is what makes DRF answer 401 rather than 403
        when no credential was supplied, and DRF builds this header from
        `authenticators[0]` alone -- which is this class.

        That matters beyond politeness. With MCP OAuth on, the challenge has to
        carry the RFC 9728 `resource_metadata` hint, because that hint is how
        an MCP client discovers the authorization server; a client that never
        sees it cannot connect unaided. That responsibility used to belong to
        the position this class now occupies, so it is delegated rather than
        dropped -- see the ordering note in template/settings/base.py.
        """
        if settings.MCP_OAUTH_ENABLED:
            from apps.mcp_oauth.authentication import BearerTokenAuthentication

            return BearerTokenAuthentication().authenticate_header(request)
        return f'{KEYWORD} realm="api"'

    @staticmethod
    def _raw_token(request):
        header = request.META.get(AUTH_HEADER, '')
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != KEYWORD:
            return None
        return parts[1]

    @classmethod
    def _is_ours(cls, request):
        """Whether this token claims our issuer.

        Deliberately unverified -- see the module docstring. A malformed token
        is not ours either: there is nothing to route on, and letting the next
        authenticator produce the error keeps one class responsible for one
        scheme.
        """
        token = cls._raw_token(request)
        if token is None:
            return False

        try:
            claims = jwt.decode(
                token,
                options={'verify_signature': False},
                algorithms=[settings.SIMPLE_JWT['ALGORITHM']],
            )
        except jwt.PyJWTError:
            return False

        return claims.get('iss') == settings.TOKEN_ISSUER
