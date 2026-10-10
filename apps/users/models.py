from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class CustomUser(AbstractUser):
    """Project user. Signs in with an email address; there is no username.

    Rename the choice sets and add the fields your product needs -- this
    model exists so that is a migration rather than a rewrite.
    """

    class AccountType(models.TextChoices):
        FREE = 'FREE', _('Free')
        PRO = 'PRO', _('Pro')

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        USER = 'USER', _('User')

    # Removes the field AbstractUser defines. The email address is the
    # identifier: it is what people remember, and a second unique handle is
    # one more thing to collide on at signup and to scrub on deletion.
    username = None

    # `unique=True` is what Django requires of USERNAME_FIELD. The
    # case-insensitive constraint in Meta is the one that actually matters,
    # because every lookup by address -- sign-in, password reset, email
    # verification, invitations -- matches without regard to case.
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={'unique': _('A user with that email already exists.')},
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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    # Prompted for by `createsuperuser` in addition to USERNAME_FIELD and the
    # password. Empty: nothing else is needed to sign in.
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='users_customuser_email_ci_unique',
                violation_error_message=_('A user with that email already exists.'),
            ),
        ]

    def __str__(self):
        return self.email

    @property
    def is_anonymized(self):
        return self.date_deleted is not None

    def get_display_name(self):
        full_name = self.get_full_name().strip()
        return full_name or self.email
