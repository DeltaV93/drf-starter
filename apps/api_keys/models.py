"""Long-lived credentials for programmatic access.

Session cookies work for a browser and for nothing else: no CLI, no CI job, no
server-to-server integration. This is the other credential.

The key is shown once, at creation, and never again. Only a digest is stored,
so a database dump, a backup or a stray log line yields nothing usable.
"""

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

# A visible, non-secret label so a key is identifiable in a list and in logs
# without the secret ever being written down.
PREFIX_LENGTH = 8
SECRET_BYTES = 32


def generate_key():
    """Return (full_key, prefix, digest).

    The full key is `prefix.secret`. Carrying the prefix in the key itself is
    what lets lookup be one indexed query rather than a scan that hashes every
    row -- and it means a leaked key found in a log can be identified and
    revoked without knowing the secret.
    """
    prefix = secrets.token_hex(PREFIX_LENGTH // 2)
    secret = secrets.token_urlsafe(SECRET_BYTES)
    return f'{prefix}.{secret}', prefix, hash_secret(secret)


def hash_secret(secret):
    """Digest the secret half of a key.

    SHA-256, not a password hash: the secret is 32 bytes of entropy, so there
    is nothing to brute-force, and verification is on the hot path of every
    authenticated API request.
    """
    return hashlib.sha256(secret.encode()).hexdigest()


def split_key(raw_key):
    """Split `prefix.secret`. Returns (None, None) for anything malformed."""
    if not raw_key or raw_key.count('.') != 1:
        return None, None
    prefix, secret = raw_key.split('.', 1)
    if not prefix or not secret:
        return None, None
    return prefix, secret


class APIKeyQuerySet(models.QuerySet):
    def usable(self):
        return self.filter(revoked_at__isnull=True).exclude(
            expires_at__isnull=False, expires_at__lte=timezone.now()
        )


class APIKey(models.Model):
    """A credential belonging to one user.

    Scoped to a user rather than to an organization even when teams are on:
    keeping every feature user-scoped is what stops the flags depending on one
    another. An organization's keys are its members' keys.
    """

    class Scope(models.TextChoices):
        READ = 'read', 'Read only'
        WRITE = 'write', 'Read and write'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_keys'
    )
    name = models.CharField(
        max_length=100, help_text='What this key is for, so it can be revoked knowingly.'
    )

    prefix = models.CharField(max_length=PREFIX_LENGTH, unique=True, db_index=True)
    hashed_secret = models.CharField(max_length=64)

    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.READ)

    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    # Written on use, so an unused key can be found and removed. Throttled to
    # one write a minute -- see authentication.py.
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = APIKeyQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API key'

    def __str__(self):
        return f'{self.name} ({self.prefix}…)'

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_usable(self):
        return not self.is_revoked and not self.is_expired

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])
