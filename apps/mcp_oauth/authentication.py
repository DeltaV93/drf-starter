"""Authenticating a request with an OAuth bearer token.

Registered in DEFAULT_AUTHENTICATION_CLASSES only when MCP_OAUTH_ENABLED is
on, alongside SessionAuthentication rather than instead of it -- the browser
keeps using cookies.

This class does two things and delegates the third. It resolves a verified
token to a Django user, and it enforces the read/write scope split. The
verification itself -- signature, audience, issuer, expiry, algorithm -- lives
in `validation.py`, which is the security-critical half and is tested by
forging tokens at it.

## Why the MCP endpoint gets this for free

`apps/mcp_server` forwards the caller's `Authorization` header unchanged into
an in-process request through the whole Django stack. So the moment this class
is in the default list, every MCP tool accepts bearer tokens -- there is no
MCP-specific auth path to keep in step, and no second implementation to get
subtly wrong. Swapping API keys for OAuth is a settings change.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import SAFE_METHODS

from .metadata import metadata_url
from .validation import InvalidToken, validate

HEADER = 'HTTP_AUTHORIZATION'
KEYWORD = 'Bearer'


class BearerTokenAuthentication(BaseAuthentication):
    """`Authorization: Bearer <jwt>`.

    Not a subclass of SessionAuthentication, for the same reason the API-key
    class is not: DRF's session class enforces CSRF for cookie-authenticated
    requests, and a token-authenticated request has no cookie to enforce
    against.
    """

    keyword = KEYWORD

    def authenticate(self, request):
        token = self._raw_token(request)
        if token is None:
            return None  # Not our scheme. Let the next authenticator try.

        try:
            claims = validate(token)
        except InvalidToken:
            # One message for every failure. Telling the caller whether a
            # token expired, was for another audience or was forged outright
            # turns the endpoint into an oracle for probing the configuration.
            raise exceptions.AuthenticationFailed('Invalid token.') from None

        user = self._user_for(claims)
        if user is None or not user.is_active:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not self._scope_allows(claims, request):
            # Raised here rather than left to a permission class, for the
            # reason apps/api_keys/authentication.py records: declaring
            # `permission_classes` on a view *replaces* the defaults, so a
            # permission class is enforcement a view can forget. Every
            # token-authenticated request passes through here.
            raise exceptions.AuthenticationFailed('This token is read-only.')

        return user, claims

    def authenticate_header(self, request):
        """The `WWW-Authenticate` challenge, which is also discovery.

        RFC 9728 says a resource server points at its metadata document from
        this header. That is how a client that knows only the URL finds the
        authorization server, so a fresh MCP client can complete the flow with
        nothing configured but this endpoint.

        Returning it at all is also what makes DRF answer 401 rather than 403
        when no credential was supplied.
        """
        return f'{self.keyword} resource_metadata="{metadata_url()}"'

    @staticmethod
    def _raw_token(request):
        header = request.META.get(HEADER, '')
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != KEYWORD:
            return None
        return parts[1]

    @staticmethod
    def _user_for(claims):
        """The account the token speaks for, or None.

        A token for an unknown subject is refused, never used to create an
        account. The authorization server delegates login to this application,
        so every legitimate subject already exists here -- an unknown one means
        the token came from somewhere it should not have.
        """
        identifier = claims.raw.get(settings.MCP_OAUTH_SUBJECT_CLAIM)
        if not identifier:
            return None
        try:
            return (
                get_user_model()
                ._default_manager.filter(**{settings.MCP_OAUTH_USER_LOOKUP_FIELD: identifier})
                .first()
            )
        except (ValueError, TypeError, FieldError):
            # A `sub` that is not a valid value for the lookup field -- a
            # non-numeric primary key, most often. Not a match, not a crash.
            return None

    @staticmethod
    def _scope_allows(claims, request):
        """A token without the write scope may not use an unsafe method."""
        required = settings.MCP_OAUTH_WRITE_SCOPE
        if not required or request.method in SAFE_METHODS:
            return True
        return claims.has_scope(required)
