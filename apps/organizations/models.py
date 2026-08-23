"""Organizations, membership and invitations.

The tenancy model for the B2B shape. Optional: gated by
settings.ORGANIZATIONS_ENABLED, and nothing outside this app holds a foreign
key to anything in it. Other features scope themselves to a user; an
organization is a lens over its members, which is what keeps the feature flags
independent of one another.
"""

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

# Long enough that guessing is hopeless, short enough to survive an email
# client's line wrapping without being broken across lines.
INVITATION_TOKEN_BYTES = 32


def generate_invitation_token():
    """Return a fresh raw token. Only ever shown once, in the invitation email."""
    return secrets.token_urlsafe(INVITATION_TOKEN_BYTES)


def hash_invitation_token(raw_token):
    """Hash a token for storage and lookup.

    Invitation tokens grant access to an organization's data, so the database
    stores only a digest: a dump, a backup or a stray log line then reveals
    nothing usable. SHA-256 rather than a password hash because the token is
    already high-entropy random -- there is nothing to brute-force -- and
    lookup has to be a single indexed query.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


class Organization(models.Model):
    """A tenant. Owns nothing directly; membership is the relationship."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.name) or 'org'
        slug = base
        suffix = 2
        while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{suffix}'
            suffix += 1
        return slug

    @property
    def owners(self):
        return self.memberships.filter(role=Membership.Role.OWNER)

    @property
    def seats_used(self):
        """Accepted members plus invitations still outstanding.

        Pending invitations count. Otherwise a plan limit could be walked past
        by sending more invitations than seats and letting them all be
        accepted.
        """
        return self.memberships.count() + self.invitations.pending().count()


class Membership(models.Model):
    """A user's place in an organization.

    Deliberately separate from CustomUser.role, which is a global,
    product-wide role. This one is per-organization: the same person can own
    one and be a plain member of another.
    """

    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Owner'
        ADMIN = 'ADMIN', 'Admin'
        MEMBER = 'MEMBER', 'Member'

    # Roles allowed to manage members, invitations and the organization itself.
    MANAGER_ROLES = (Role.OWNER, Role.ADMIN)

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships'
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization__name', 'user__email']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'user'], name='unique_membership_per_org'
            )
        ]

    def __str__(self):
        return f'{self.user} in {self.organization} ({self.role})'

    @property
    def can_manage(self):
        return self.role in self.MANAGER_ROLES

    @property
    def is_last_owner(self):
        """True when removing or demoting this membership would orphan the org.

        An organization with no owner cannot be administered or cancelled by
        anyone, and recovering it needs a database shell.
        """
        if self.role != self.Role.OWNER:
            return False
        return not (
            Membership.objects.filter(organization=self.organization, role=self.Role.OWNER)
            .exclude(pk=self.pk)
            .exists()
        )


class InvitationQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(accepted_at__isnull=True, expires_at__gt=timezone.now())


class Invitation(models.Model):
    """An offer of membership, addressed to an email and carrying a secret.

    Single use and time limited. The raw token exists only in the email; the
    row keeps a digest.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='invitations'
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=16, choices=Membership.Role.choices, default=Membership.Role.MEMBER
    )

    token_hash = models.CharField(max_length=64, unique=True)

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
    )

    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = InvitationQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # One live invitation per address per organization. Re-inviting
            # replaces rather than accumulating, so revoking one is enough.
            models.UniqueConstraint(
                fields=['organization', 'email'],
                condition=models.Q(accepted_at__isnull=True),
                name='one_pending_invitation_per_email',
            )
        ]

    def __str__(self):
        return f'{self.email} -> {self.organization}'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_pending(self):
        return self.accepted_at is None and not self.is_expired
