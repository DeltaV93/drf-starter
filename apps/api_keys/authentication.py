"""Authenticating a request with an API key.

Registered in DEFAULT_AUTHENTICATION_CLASSES only when API_KEYS_ENABLED is on,
alongside SessionAuthentication rather than instead of it -- the browser keeps
using cookies.
"""

import hmac

from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import SAFE_METHODS

from .models import APIKey, hash_secret, split_key

HEADER = 'HTTP_AUTHORIZATION'
KEYWORD = 'Api-Key'

# last_used_at is a convenience, not an audit trail. Writing it on every
# request would put a write on the hot path of a read-only API; a minute of
# granularity is enough to answer "is this key still in use?".
LAST_USED_RESOLUTION_SECONDS = 60


class APIKeyAuthentication(BaseAuthentication):
    """`Authorization: Api-Key <prefix>.<secret>`.

    Deliberately NOT a subclass of SessionAuthentication: DRF's session class
    enforces CSRF for cookie-authenticated requests, and a key-authenticated
    request has no cookie and no CSRF token to enforce against. Keeping them
    separate is also what stops a key being usable as a session -- see
    enforce_csrf below.
    """

    keyword = KEYWORD

    def authenticate(self, request):
        raw_key = self._raw_key(request)
        if raw_key is None:
            return None  # Let the next authenticator try.

        prefix, secret = split_key(raw_key)
        if prefix is None:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        key = APIKey.objects.select_related('user').filter(prefix=prefix).first()

        # One message for every failure. Distinguishing "no such key" from
        # "wrong secret" from "revoked" would let someone enumerate valid
        # prefixes.
        if key is None or not self._secret_matches(key, secret):
            raise exceptions.AuthenticationFailed('Invalid API key.')
        if not key.is_usable:
            raise exceptions.AuthenticationFailed('Invalid API key.')
        if not key.user.is_active:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        if not self._scope_allows(key, request):
            # Deliberately raised here rather than left to a permission class.
            #
            # HasWriteScope exists and is correct, but `permission_classes` on
            # a view *replaces* DEFAULT_PERMISSION_CLASSES rather than adding
            # to them -- so enforcement was opt-in, nothing opted in, and a
            # read-only key could write anywhere. Authentication is the single
            # choke point every key-authenticated request passes through, and
            # the one a view cannot forget.
            raise exceptions.AuthenticationFailed('This API key is read-only.')

        self._touch(key)
        return key.user, key

    def authenticate_header(self, request):
        """Makes DRF answer 401 rather than 403 when no credential was given."""
        return self.keyword

    @staticmethod
    def _raw_key(request):
        header = request.META.get(HEADER, '')
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != KEYWORD:
            return None
        return parts[1]

    @staticmethod
    def _scope_allows(key, request):
        """A read-only key may not use an unsafe method."""
        if key.scope == APIKey.Scope.WRITE:
            return True
        return request.method in SAFE_METHODS

    @staticmethod
    def _secret_matches(key, secret):
        # Constant time, so the comparison cannot be used as an oracle.
        return hmac.compare_digest(key.hashed_secret, hash_secret(secret))

    @staticmethod
    def _touch(key):
        now = timezone.now()
        if (
            key.last_used_at is None
            or (now - key.last_used_at).total_seconds() >= LAST_USED_RESOLUTION_SECONDS
        ):
            APIKey.objects.filter(pk=key.pk).update(last_used_at=now)
            key.last_used_at = now
