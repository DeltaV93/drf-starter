"""Organization-scoped permissions.

Both resolve the active organization through context.active_membership, which
reads it from the session rather than from anything the caller sent, so a view
cannot be talked into answering for an organization the request never selected.
"""

from rest_framework.permissions import BasePermission

from .context import active_membership
from .models import Membership


class IsOrgMember(BasePermission):
    """Belongs to the active organization, in any role."""

    message = 'You are not a member of this organization.'

    def has_permission(self, request, view):
        return active_membership(request) is not None


class IsOrgAdmin(BasePermission):
    """Owner or admin of the active organization.

    Members can read; changing membership, invitations or the organization
    itself needs this.
    """

    message = 'You must be an owner or admin of this organization.'

    def has_permission(self, request, view):
        membership = active_membership(request)
        return membership is not None and membership.role in Membership.MANAGER_ROLES
