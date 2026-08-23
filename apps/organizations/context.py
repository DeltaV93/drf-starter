"""Resolving which organization a request is acting for.

A helper rather than middleware, for two reasons.

Middleware that reads ``request.user`` forces the session and user lookup on
every request, including the ones Django deliberately keeps lazy -- static
files, health probes, the SPA catch-all. And attaching a SimpleLazyObject that
may resolve to None is a trap: the wrapper is never ``is None``, so the
obvious ``if request.membership is not None`` silently passes for everyone.

Calling active_membership(request) is explicit, lazy, and caches per request.
"""

from django.conf import settings

# Which organization the caller last switched to. Session-backed on purpose:
# taking it from a header or the request body would let a caller name an
# organization they do not belong to, and every view would have to re-check.
SESSION_KEY = 'active_organization_id'

_CACHE_ATTR = '_active_membership'


def active_membership(request):
    """The caller's membership of the organization they are acting for, or None.

    Falls back to their earliest membership when the session names none, so a
    user with exactly one organization never has to choose it.
    """
    if not settings.ORGANIZATIONS_ENABLED:
        return None

    cached = getattr(request, _CACHE_ATTR, Ellipsis)
    if cached is not Ellipsis:
        return cached

    membership = _resolve(request)
    setattr(request, _CACHE_ATTR, membership)
    return membership


def active_organization(request):
    membership = active_membership(request)
    return membership.organization if membership else None


def set_active_organization(request, organization):
    """Remember the caller's choice for subsequent requests."""
    request.session[SESSION_KEY] = organization.pk
    if hasattr(request, _CACHE_ATTR):
        delattr(request, _CACHE_ATTR)


def _resolve(request):
    from .models import Membership

    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None

    memberships = Membership.objects.select_related('organization').filter(user=user)

    chosen_id = request.session.get(SESSION_KEY)
    if chosen_id is not None:
        membership = memberships.filter(organization_id=chosen_id).first()
        if membership is not None:
            return membership
        # They left the organization, or it was deleted. Clear the stale
        # pointer rather than leaving the session naming something gone.
        request.session.pop(SESSION_KEY, None)

    return memberships.order_by('created_at', 'pk').first()
