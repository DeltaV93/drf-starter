"""The audit vocabulary, and a call that works whether or not it is enabled.

Lives in core rather than in apps/audit because the call sites are in apps
that are always installed, and apps/audit is not. Importing the real module at
the top of authentication/views.py would make AUDIT_LOG_ENABLED=false an
ImportError -- which is exactly the sort of dependency between optional
features the flags are meant to avoid.

The action names are defined here, and apps/audit/models.py builds its choices
from them, so there is one list rather than two that drift.
"""

from django.conf import settings


class AuditAction:
    """Every action that may be recorded.

    A fixed vocabulary, not free-form strings: it is what makes the log
    searchable, and what lets metadata be allow-listed per action.
    """

    LOGIN_SUCCEEDED = 'login.succeeded'
    LOGIN_FAILED = 'login.failed'
    LOGOUT = 'logout'
    PASSWORD_CHANGED = 'password.changed'
    PASSWORD_RESET_REQUESTED = 'password.reset_requested'
    EMAIL_VERIFIED = 'email.verified'
    ACCOUNT_CREATED = 'account.created'
    ACCOUNT_DELETED = 'account.deleted'
    API_KEY_CREATED = 'api_key.created'
    API_KEY_REVOKED = 'api_key.revoked'
    MEMBER_INVITED = 'member.invited'
    MEMBER_JOINED = 'member.joined'
    MEMBER_REMOVED = 'member.removed'
    MEMBER_ROLE_CHANGED = 'member.role_changed'
    TWO_FACTOR_ENABLED = 'two_factor.enabled'
    TWO_FACTOR_DISABLED = 'two_factor.disabled'
    MCP_SERVER_CALLED = 'mcp_client.called'

    @classmethod
    def all(cls):
        return [
            value
            for name, value in vars(cls).items()
            if not name.startswith('_') and isinstance(value, str)
        ]


def audit(action, *, actor=None, request=None, target='', **metadata):
    """Record an event, or do nothing when the audit log is switched off.

    Never raises: auditing must not be able to fail the thing it audits. A
    login that 500s because the log table is full is a worse outcome than a
    missing row.
    """
    if not settings.AUDIT_LOG_ENABLED:
        return None

    from apps.audit.events import record

    return record(action, actor=actor, request=request, target=target, **metadata)
