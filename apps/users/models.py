from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Project user.

    Rename the choice sets and add the fields your product needs -- this
    model exists so that is a migration rather than a rewrite.
    """

    class AccountType(models.TextChoices):
        FREE = 'FREE', _('Free')
        PRO = 'PRO', _('Pro')

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        USER = 'USER', _('User')

    # Unique because password reset and email verification both look users up
    # by address; without this, two accounts sharing an email make that lookup
    # ambiguous.
    email = models.EmailField(_('email address'), unique=True)

    account_type = models.CharField(
        max_length=16,
        choices=AccountType.choices,
        default=AccountType.FREE,
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)

    phone_number = models.CharField(max_length=32, blank=True, default='')

    email_verified = models.BooleanField(
        default=False,
        help_text=_('Set once the user follows the link in their verification email.'),
    )

    # Set by the GDPR anonymization path instead of deleting the row, so
    # foreign keys stay intact and the deletion remains auditable.
    date_deleted = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.username

    @property
    def is_anonymized(self):
        return self.date_deleted is not None

    def get_display_name(self):
        full_name = self.get_full_name().strip()
        return full_name or self.username
