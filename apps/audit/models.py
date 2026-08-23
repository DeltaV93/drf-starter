"""An append-only record of the things worth being able to answer for.

Written from explicit call sites, not from a blanket signal. A signal on every
save records mostly noise and, worse, records whatever happens to be on the
model -- which is how a password hash or a card number ends up in an audit
table nobody thought was sensitive.
"""

from django.conf import settings
from django.db import models

from apps.core.audit import AuditAction


class Action(models.TextChoices):
    """The recordable actions.

    Values come from apps.core.audit.AuditAction so there is one definition of
    each string. That module is where the call sites import from, because it
    is always installed and this app is not. A member missing here is caught
    by test_vocabulary.py rather than by a silent gap in the choices.
    """

    LOGIN_SUCCEEDED = AuditAction.LOGIN_SUCCEEDED, 'Login succeeded'
    LOGIN_FAILED = AuditAction.LOGIN_FAILED, 'Login failed'
    LOGOUT = AuditAction.LOGOUT, 'Logout'
    PASSWORD_CHANGED = AuditAction.PASSWORD_CHANGED, 'Password changed'
    PASSWORD_RESET_REQUESTED = AuditAction.PASSWORD_RESET_REQUESTED, 'Password reset requested'
    EMAIL_VERIFIED = AuditAction.EMAIL_VERIFIED, 'Email verified'
    ACCOUNT_CREATED = AuditAction.ACCOUNT_CREATED, 'Account created'
    ACCOUNT_DELETED = AuditAction.ACCOUNT_DELETED, 'Account deleted'
    API_KEY_CREATED = AuditAction.API_KEY_CREATED, 'API key created'
    API_KEY_REVOKED = AuditAction.API_KEY_REVOKED, 'API key revoked'
    MEMBER_INVITED = AuditAction.MEMBER_INVITED, 'Member invited'
    MEMBER_JOINED = AuditAction.MEMBER_JOINED, 'Member joined'
    MEMBER_REMOVED = AuditAction.MEMBER_REMOVED, 'Member removed'
    MEMBER_ROLE_CHANGED = AuditAction.MEMBER_ROLE_CHANGED, 'Member role changed'
    TWO_FACTOR_ENABLED = AuditAction.TWO_FACTOR_ENABLED, 'Two-factor enabled'
    TWO_FACTOR_DISABLED = AuditAction.TWO_FACTOR_DISABLED, 'Two-factor disabled'


class AuditEvent(models.Model):
    """One recorded action.

    There is no update path and no delete path, and the admin is registered
    read-only: a log that can be edited answers no question it was kept for.
    Retention is the one exception, and it is a management command that drops
    whole rows by age rather than anything that can alter one.
    """

    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)

    # SET_NULL, not CASCADE: deleting a user must not erase the record that
    # they were deleted, which is often the entry that matters most.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    # Kept separately because the actor row may be anonymised or gone.
    actor_label = models.CharField(max_length=254, blank=True, default='')

    # What was acted on, as text rather than a generic foreign key: the target
    # may be a row that no longer exists, and a real relation would make this
    # app depend on the optional ones.
    target = models.CharField(max_length=254, blank=True, default='')

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True, default='')

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['actor', '-created_at'])]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.actor_label}'

    def save(self, *args, **kwargs):
        """Append only. An existing row cannot be rewritten."""
        if self.pk is not None:
            raise ValueError(
                'Audit events are append-only. Record a new event instead of '
                'editing an existing one.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            'Audit events are append-only. Use the prune_audit_log command to '
            'drop old entries by age.'
        )
