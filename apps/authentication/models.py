"""Two-factor enrolment.

The rest of this app is views, serializers and permissions; the user model
lives in apps.users. These two tables exist because TWO_FACTOR_ENABLED gates
behaviour rather than INSTALLED_APPS -- see apps/authentication/two_factor.py.
"""

from django.conf import settings
from django.db import models


class TwoFactorDevice(models.Model):
    """One TOTP enrolment per user.

    A device is not active until confirmed_at is set. Enrolling without
    proving the codes work is how people lock themselves out: the secret is
    stored, the app is not really configured, and the next login is
    unanswerable.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='two_factor'
    )

    # Encrypted; see two_factor.encrypt_secret. Never returned by any endpoint
    # after enrolment -- the provisioning URI is shown once and then only codes
    # are exchanged.
    encrypted_secret = models.CharField(max_length=255)

    confirmed_at = models.DateTimeField(null=True, blank=True)

    # The TOTP step of the last accepted code. A code stays valid for its whole
    # window, so without this one read off a shoulder or a proxy log can be
    # replayed within it.
    last_used_step = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'two-factor device'

    def __str__(self):
        state = 'confirmed' if self.is_confirmed else 'pending'
        return f'2FA for {self.user} ({state})'

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None


class RecoveryCode(models.Model):
    """A single-use way back in when the authenticator is gone.

    Only a digest is stored, so the codes are recoverable by nobody after the
    one screen that showed them.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recovery_codes'
    )
    hashed_code = models.CharField(max_length=64, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'hashed_code'], name='unique_recovery_code_per_user'
            )
        ]

    def __str__(self):
        return f'Recovery code for {self.user} ({"used" if self.used_at else "unused"})'
