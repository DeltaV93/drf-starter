"""Resolving which organization a request is acting for.

A helper rather than middleware, for two reasons.

Middleware that reads ``request.user`` forces the session and user lookup on
every request, including the ones Django deliberately keeps lazy -- static
files, health probes, the SPA catch-all. And attaching a SimpleLazyObject that
may resolve to None is a trap: the wrapper is never ``is None``, so the
obvious ``if request.membership is not None`` silently passes for everyone.

Calling active_membership(request) is explicit, lazy, and caches per request.

## Two clients, two ways of remembering

The browser's choice lives in its session, because it has one and the cookie
carries it for free.

A bearer-token client has no session, so it names the organization on each
request with ``X-Organization``. That is not the loophole it looks like: the
value is resolved against the caller's *own* memberships below, exactly as the
session's is, so the worst an attacker who controls the header can do is act
as an organization the user already belongs to. What would be unsafe is a view
trusting an id from the request body -- which is why this stays the only place
either source is read.
"""

from django.conf import settings

# Which organization the caller last switched to, for a client with a session.
SESSION_KEY = 'active_organization_id'

# The same choice, for a client without one. Carries a slug rather than a
# primary key: it is a value the app stores and shows, and a slug is the
# identifier the rest of the API already speaks.
HEADER = 'HTTP_X_ORGANIZATION'
HEADER_NAME = 'X-Organization'

_CACHE_ATTR = '_active_membership'


def active_membership(request):
    """The caller's membership of the organization they are acting for, or None.

    Falls back to their earliest membership when nothing names one, so a user
    with exactly one organization never has to choose it.
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
    """Remember the caller's choice for subsequent requests.

    A no-op for a token client, which has no session to remember it in -- that
    client sends ``X-Organization`` instead, and the switch endpoint's response
    is what tells it which slug to send.
    """
    if hasattr(request, 'session'):
        request.session[SESSION_KEY] = organization.pk
    if hasattr(request, _CACHE_ATTR):
        delattr(request, _CACHE_ATTR)


def _resolve(request):
    from .models import Membership

    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None

    memberships = Membership.objects.select_related('organization').filter(user=user)

    # The header first. It is per-request and explicit, so when both are
    # present it is the more recent instruction -- and for the client that
    # sends it there is no session value to lose.
    slug = request.META.get(HEADER)
    if slug:
        membership = memberships.filter(organization__slug=slug).first()
        if membership is not None:
            return membership
        # Naming an organization they do not belong to falls through to the
        # default rather than erroring: the header is a preference, and a
        # stale one on a device left signed in is not worth a 400 on every
        # request. Views that act *on* an organization still 404 by slug.

    session = getattr(request, 'session', None)
    chosen_id = session.get(SESSION_KEY) if session is not None else None
    if chosen_id is not None:
        membership = memberships.filter(organization_id=chosen_id).first()
        if membership is not None:
            return membership
        # They left the organization, or it was deleted. Clear the stale
        # pointer rather than leaving the session naming something gone.
        session.pop(SESSION_KEY, None)

    return memberships.order_by('created_at', 'pk').first()
