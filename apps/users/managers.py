from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for a user model that signs in with an email address.

    Django's own `UserManager` takes a username as its first argument, which
    this model does not have; this is the manager Django's documentation asks
    for when `USERNAME_FIELD` is changed.
    """

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        # Lowercase the whole address, not just the domain as Django does.
        # Mailbox names are case-sensitive in theory and never in practice,
        # and treating Ada@ and ada@ as two accounts is the bug users notice.
        # Every write path goes through here -- create_user, and the admin's
        # forms via AbstractUser.clean() -- which is what the case-insensitive
        # unique constraint on the model relies on.
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        # What ModelBackend calls on sign-in. Matched without regard to case,
        # so an address typed with a capital still finds the account.
        return self.get(email__iexact=email)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
