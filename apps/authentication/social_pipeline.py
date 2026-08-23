"""The social-auth pipeline, and the one decision in it that matters.

python-social-auth's default pipeline includes `associate_by_email`, which
hands a social identity the existing account with the same address. That is an
account-takeover path: anyone who can make a provider assert an address --
through a provider that does not verify email, an unverified account on one
that usually does, or a compromised one -- inherits the password account.

This pipeline replaces it. An unrecognised social identity whose email already
belongs to someone is refused, and the user is told to sign in with their
password and link deliberately.
"""

from social_core.exceptions import AuthException

from apps.core.audit import AuditAction, audit

# Nothing at module level may touch the model registry: settings.py imports
# PIPELINE below, which runs long before the apps are loaded.

# Shown to the user when their social email matches an existing account.
LINK_REQUIRED_MESSAGE = (
    'An account already exists for that email address. Sign in with your '
    'password first, then link this provider from your profile.'
)


class EmailAlreadyRegistered(AuthException):
    def __str__(self):
        return LINK_REQUIRED_MESSAGE


def refuse_silent_takeover(strategy, details, backend, user=None, *args, **kwargs):
    """Refuse to hand an existing account to an unlinked social identity.

    Runs before create_user. If the identity is already associated with a user
    (`user` is set), social_core has matched it on the provider's stable id and
    there is nothing to decide.
    """
    del strategy, args, kwargs

    if user is not None:
        return None

    email = (details.get('email') or '').strip().lower()
    if not email:
        return None

    from django.contrib.auth import get_user_model

    existing = get_user_model().objects.filter(email__iexact=email).first()
    if existing is None:
        return None

    audit(
        AuditAction.LOGIN_FAILED,
        target=email,
        reason='social_email_already_registered',
    )
    raise EmailAlreadyRegistered(backend)


def mark_email_verified(strategy, details, user=None, *args, **kwargs):
    """Trust the provider's address only when the provider says it verified it.

    Google reports `email_verified`; several providers report nothing. Absent a
    positive signal the address stays unverified and the normal confirmation
    email applies -- which is also what stops a provider that does not verify
    from minting pre-verified accounts here.
    """
    del strategy, args

    if user is None or not hasattr(user, 'email_verified') or user.email_verified:
        return None

    response = kwargs.get('response') or {}
    if response.get('email_verified') is True and details.get('email'):
        user.email_verified = True
        user.save(update_fields=['email_verified'])

    return None
