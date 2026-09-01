"""User creation, keyed by email.

`AbstractUser` ships with a manager whose `create_user` takes the username
first and requires it. Username is optional here and email is the identifier,
so both signatures move: `create_user(email, password, **extra)`. A username
passed in `extra` is still honoured -- it is a field like any other now.
"""

from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    """Creates users by email address. `username` is optional."""

    @classmethod
    def normalize_email(cls, email):
        """Lowercase the whole address, not just its domain.

        Django's version lowercases the domain and leaves the local part
        alone, because the RFC allows a server to treat `Ada@` and `ada@` as
        two mailboxes. In practice no provider does, and here the address is
        the identifier: two rows differing only in case would be two accounts
        for one person, each able to register over the other's absence, and
        every lookup would have to remember to be case-insensitive. Storing
        one form removes the question.

        `CustomUser.save()` applies this to every write, and `AbstractUser`
        already calls it from `clean()`, so the admin normalizes too.
        """
        return super().normalize_email(email).strip().lower()

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address.')

        email = self.normalize_email(email)

        # Blank and absent are the same thing for an optional unique column,
        # and only one of them can appear twice. See CustomUser.save().
        username = extra_fields.pop('username', None) or None
        if username:
            username = self.model.normalize_username(username)

        user = self.model(email=email, username=username, **extra_fields)
        # None means "unusable", which is what a social signup needs: the
        # account exists but no password will ever authenticate it.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
