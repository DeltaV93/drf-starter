from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    """Require a confirmed email address.

    Not applied globally: signup leaves the user logged in but unverified so
    they can look around. Add this to the views that must not be reachable
    until the address is confirmed.
    """

    message = 'Confirm your email address to use this feature.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.email_verified)
