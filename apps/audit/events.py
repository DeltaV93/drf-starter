"""Recording an event.

`record()` is the only way in, and it allow-lists metadata per action. That is
the point: a caller passing a whole request body, a serializer's validated_data
or a model's __dict__ would put passwords, tokens and card numbers into a table
that is deliberately hard to edit and deliberately kept for a long time.
"""

from django.conf import settings

from utils.logging_utils import get_logger

from .models import Action, AuditEvent

logger = get_logger(__name__)

# Which metadata keys each action may carry. Anything else is dropped, so a
# careless call site cannot widen what is stored.
ALLOWED_METADATA = {
    Action.LOGIN_FAILED: {'reason'},
    Action.API_KEY_CREATED: {'prefix', 'scope', 'expires_at'},
    Action.API_KEY_REVOKED: {'prefix'},
    Action.MEMBER_INVITED: {'organization', 'role'},
    Action.MEMBER_JOINED: {'organization', 'role'},
    Action.MEMBER_REMOVED: {'organization'},
    Action.MEMBER_ROLE_CHANGED: {'organization', 'from_role', 'to_role'},
    Action.ACCOUNT_DELETED: {'reason'},
}

# Never stored, whatever an action's allow-list says and whatever a caller
# passes. A belt-and-braces list for the keys that would be most damaging.
NEVER_STORED = {
    'password',
    'password1',
    'password2',
    'password_confirm',
    'new_password',
    'old_password',
    'token',
    'secret',
    'key',
    'api_key',
    'csrfmiddlewaretoken',
    'authorization',
    'card',
    'card_number',
    'cvv',
}

USER_AGENT_MAX_LENGTH = 400


def record(action, *, actor=None, request=None, target='', **metadata):
    """Append an audit event. Never raises.

    Auditing must not be able to fail the thing it is auditing: a login that
    500s because the log table is full is a worse outcome than a missing row,
    so every failure here is logged and swallowed.
    """
    if not settings.AUDIT_LOG_ENABLED:
        return None

    try:
        return AuditEvent.objects.create(
            action=action,
            actor=actor if getattr(actor, 'pk', None) else None,
            actor_label=_actor_label(actor),
            target=str(target)[:254],
            ip_address=client_ip(request),
            user_agent=_user_agent(request),
            metadata=_filter_metadata(action, metadata),
        )
    except Exception:
        logger.exception('Could not record audit event %s', action)
        return None


def client_ip(request):
    """The caller's address, honouring a single proxy hop.

    X-Forwarded-For is client-supplied and trivially spoofed, so the leftmost
    entry is only meaningful behind a proxy that overwrites the header. That is
    the deployment this template describes; if yours differs, narrow this.
    """
    if request is None:
        return None

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        candidate = forwarded.split(',')[0].strip()
        if candidate:
            return candidate[:45] or None

    return request.META.get('REMOTE_ADDR') or None


def _actor_label(actor):
    """A durable description, since the actor row may later be anonymised."""
    if actor is None or not getattr(actor, 'pk', None):
        return ''
    return (getattr(actor, 'email', '') or str(actor))[:254]


def _user_agent(request):
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:USER_AGENT_MAX_LENGTH]


def _filter_metadata(action, metadata):
    allowed = ALLOWED_METADATA.get(action, set())
    filtered = {}

    for key, value in metadata.items():
        if key.lower() in NEVER_STORED:
            logger.warning('Refused to store audit metadata key %r for %s', key, action)
            continue
        if key not in allowed:
            logger.warning('Dropped unexpected audit metadata key %r for %s', key, action)
            continue
        filtered[key] = value

    return filtered
