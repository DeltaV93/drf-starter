from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


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

    # The identifier. Unique because password reset, email verification and
    # sign-in all look users up by address; without this, two accounts sharing
    # an email make that lookup ambiguous.
    email = models.EmailField(_('email address'), unique=True)

    # Optional, and NULL rather than '' when unset -- a unique column admits
    # any number of NULLs but only one empty string, so storing '' would let
    # the second account without a handle collide with the first. `save()`
    # below is what guarantees it, because a blank form field yields ''.
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        default=None,
        validators=[UnicodeUsernameValidator()],
        help_text=_(
            'Optional. 150 characters or fewer. Letters, digits and @/./+/-/_ only. '
            'Sign-in uses the email address; a username is an alternative for it.'
        ),
        error_messages={'unique': _('A user with that username already exists.')},
    )

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

    # Sign in with the email address. `username` stays available as an
    # alternative identifier via apps.authentication.backends, but nothing
    # requires an account to have one.
    USERNAME_FIELD = 'email'
    # Emptied deliberately: these are the fields `createsuperuser` prompts for
    # *in addition* to USERNAME_FIELD, and username is no longer one.
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # '' is not a second way of saying "no username"; see the field above.
        if not self.username:
            self.username = None
        return super().save(*args, **kwargs)

    @property
    def is_anonymized(self):
        return self.date_deleted is not None

    def get_display_name(self):
        """Best available human label: real name, then handle, then email.

        Never empty -- an account with no name and no username still has to
        render somewhere, and the email is the one field it always has.
        """
        full_name = self.get_full_name().strip()
        return full_name or self.username or self.email
