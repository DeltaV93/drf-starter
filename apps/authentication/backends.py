"""Password authentication against an email address or a username.

`USERNAME_FIELD` is the email, so the stock `ModelBackend` already signs
people in by address -- but only by an exact, case-sensitive match, and only
by that field. Two things follow from usernames being optional, and this
backend is where both live:

1. Addresses are compared case-insensitively. Registration lowercases what it
   stores, but rows predating that -- or created in the admin, or by a data
   import -- do not, and "your password is wrong" is what the user would be
   told instead.
2. An account that *has* a username can still sign in with it, so a
   deployment that adopted this template before email became the identifier
   does not log its whole userbase out.

Email is resolved first and username only if no address matched, which is
what makes the outcome deterministic when one account's username happens to
be another's email address. Registration refuses to create that collision
(see `UserRegistrationSerializer.validate_username`), but existing rows and
the admin can still produce it.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

# Named explicitly wherever a user is signed in without having been through
# authenticate(), which leaves no `backend` attribute for login() to infer
# from. base.py always keeps this last in AUTHENTICATION_BACKENDS;
# SOCIAL_AUTH_ENABLED only prepends to that list.
PASSWORD_BACKEND = 'apps.authentication.backends.EmailOrUsernameBackend'


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        # DRF and Django both hand the identifier over as `username`; the
        # other two names are what a caller passing kwargs explicitly is
        # likely to use.
        identifier = username or kwargs.get('email') or kwargs.get(UserModel.USERNAME_FIELD)

        if not identifier or password is None:
            return None

        # Ordered, not merely first-found: uniqueness is enforced by the
        # serializers rather than by the column, which compares case
        # sensitively, so `Ada` and `ada` can both exist on a row the admin or
        # an import created. Whichever this picks, it has to pick the same one
        # every time -- an identifier that signs you into a different account
        # depending on the query plan is worse than one that never works.
        users = UserModel._default_manager.order_by('pk')
        user = (
            users.filter(email__iexact=identifier).first()
            # A NULL username matches nothing, so accounts without one are
            # simply never found here.
            or users.filter(username__iexact=identifier).first()
        )

        if user is None:
            # Run the hasher anyway. Returning early would make "no such user"
            # measurably faster than "wrong password", which is an account
            # enumeration oracle -- the same reason ModelBackend does this.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
