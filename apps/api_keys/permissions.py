"""Scope enforcement for key-authenticated requests."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import APIKey


class HasWriteScope(BasePermission):
    """Refuse unsafe methods to a read-only key.

    Requests that did not come from a key are unaffected: a browser session
    already carries the user's full authority, and this class is about not
    silently upgrading a read key.
    """

    message = 'This API key is read-only.'

    def has_permission(self, request, view):
        key = request.auth
        if not isinstance(key, APIKey):
            return True
        if request.method in SAFE_METHODS:
            return True
        return key.scope == APIKey.Scope.WRITE
