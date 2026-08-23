"""Assembling a user's data for export.

The other half of what GDPR asks for: gdpr_utils.py implements erasure, this
implements portability. There is no flag -- a template should not ship half a
regulation.

Collectors are registered rather than hardcoded, so an optional app contributes
its own data only when it is installed. That keeps this module free of imports
that would break with a flag switched off.
"""

import json
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings

from .logging_utils import get_logger

logger = get_logger(__name__)

# name -> callable(user) -> JSON-serialisable structure.
_COLLECTORS = {}

# Never exported, whatever a collector returns. An export is a file the user
# receives by email and may forward, store or lose; a password hash or a live
# token in it is a credential leak with extra steps.
NEVER_EXPORTED = {
    'password',
    'hashed_secret',
    'hashed_code',
    'encrypted_secret',
    'token_hash',
    'secret',
    'session_key',
}


def register_collector(name, collector):
    """Add a section to the export. Later registrations replace earlier ones."""
    _COLLECTORS[name] = collector


def collectors():
    return dict(_COLLECTORS)


def build_export(user):
    """Return the user's data as a JSON-serialisable dict.

    One collector failing must not lose the rest: a partial export the user
    can act on beats a 500 they cannot.
    """
    sections = {}

    for name, collector in sorted(_COLLECTORS.items()):
        try:
            sections[name] = scrub(collector(user))
        except Exception:
            logger.exception('Export collector %r failed for user %s', name, user.pk)
            sections[name] = {'error': 'This section could not be exported.'}

    return {
        'generated_at': _now_iso(),
        'application': settings.SPECTACULAR_SETTINGS.get('TITLE', 'Application'),
        'user_id': user.pk,
        'sections': sections,
    }


def scrub(value):
    """Drop anything whose key is a credential, at any depth.

    Belt and braces on top of each collector choosing its own fields: a
    collector that later grows a field cannot leak one by accident.
    """
    if isinstance(value, dict):
        return {
            key: scrub(item)
            for key, item in value.items()
            if str(key).lower() not in NEVER_EXPORTED
        }
    if isinstance(value, (list, tuple)):
        return [scrub(item) for item in value]
    return value


def to_json(payload):
    return json.dumps(payload, indent=2, sort_keys=True, default=_encode)


def _encode(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _now_iso():
    from django.utils import timezone

    return timezone.now().isoformat()


# --------------------------------------------------------------------------
# Built-in collectors
# --------------------------------------------------------------------------


def _profile(user):
    return {
        'username': user.get_username(),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': getattr(user, 'phone_number', ''),
        'account_type': getattr(user, 'account_type', ''),
        'role': getattr(user, 'role', ''),
        'email_verified': getattr(user, 'email_verified', None),
        'date_joined': user.date_joined,
        'last_login': user.last_login,
    }


register_collector('profile', _profile)


def register_optional_collectors():
    """Wire up the collectors whose apps may not be installed.

    Called from apps.core's AppConfig.ready(), so it runs after the app
    registry is populated and imports only what is actually there.
    """
    if settings.ORGANIZATIONS_ENABLED:
        register_collector('organizations', _organizations)
    if settings.API_KEYS_ENABLED:
        register_collector('api_keys', _api_keys)
    if settings.AUDIT_LOG_ENABLED:
        register_collector('activity', _activity)
    if settings.UPLOADS_ENABLED:
        register_collector('files', _files)
    if settings.STRIPE_ENABLED:
        register_collector('billing', _billing)


def _organizations(user):
    from apps.organizations.models import Membership

    return [
        {
            'organization': membership.organization.name,
            'role': membership.role,
            'joined': membership.created_at,
        }
        for membership in Membership.objects.select_related('organization').filter(user=user)
    ]


def _api_keys(user):
    from apps.api_keys.models import APIKey

    # The prefix only: the secret is not recoverable, and would not belong in
    # an emailed file if it were.
    return [
        {
            'name': key.name,
            'prefix': key.prefix,
            'scope': key.scope,
            'created': key.created_at,
            'last_used': key.last_used_at,
            'revoked': key.revoked_at,
        }
        for key in APIKey.objects.filter(user=user)
    ]


def _activity(user):
    from apps.audit.models import AuditEvent

    return [
        {
            'action': event.action,
            'target': event.target,
            'ip_address': event.ip_address,
            'at': event.created_at,
        }
        for event in AuditEvent.objects.filter(actor=user)[:1000]
    ]


def _files(user):
    from apps.uploads.models import Attachment

    return [
        {
            'name': attachment.original_name,
            'content_type': attachment.content_type,
            'size_bytes': attachment.size_bytes,
            'uploaded': attachment.created_at,
        }
        for attachment in Attachment.objects.filter(user=user)
    ]


def _billing(user):
    from apps.subscriptions.models import Subscription

    subscription = Subscription.objects.select_related('plan').filter(user=user).first()
    if subscription is None:
        return None
    return {
        'plan': subscription.plan.name,
        'status': subscription.status,
        'current_period_end': subscription.current_period_end,
        'created': subscription.created_at,
    }
