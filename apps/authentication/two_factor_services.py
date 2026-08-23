"""Enrolling, verifying and disabling two-factor, and the partial login.

The rules live here rather than in the views so they hold from a management
command or the shell too.
"""

from django.conf import settings
from django.utils import timezone

from apps.core.audit import AuditAction, audit

from . import two_factor
from .models import RecoveryCode, TwoFactorDevice

# The session key holding a half-finished login. Session-backed rather than a
# token in the response body: it cannot be replayed from another browser, and
# it disappears with the session.
PENDING_SESSION_KEY = 'pending_two_factor'


class TwoFactorError(Exception):
    """A rule was broken. The message is safe to show the caller."""


def device_for(user):
    return TwoFactorDevice.objects.filter(user=user).first()


def is_required_for(user):
    """True when this user must present a second factor to finish logging in."""
    if not settings.TWO_FACTOR_ENABLED:
        return False
    device = device_for(user)
    return device is not None and device.is_confirmed


def begin_enrolment(user):
    """Create (or replace) an unconfirmed device and return its provisioning URI.

    Replacing an unconfirmed device is deliberate -- someone who abandoned an
    enrolment halfway must be able to start again. A *confirmed* device is not
    replaced; disabling it first is a separate, re-authenticated step.
    """
    existing = device_for(user)
    if existing is not None and existing.is_confirmed:
        raise TwoFactorError('Two-factor is already enabled. Disable it first to re-enrol.')

    raw_secret = two_factor.generate_secret()
    TwoFactorDevice.objects.update_or_create(
        user=user,
        defaults={
            'encrypted_secret': two_factor.encrypt_secret(raw_secret),
            'confirmed_at': None,
            'last_used_step': None,
        },
    )

    return two_factor.provisioning_uri(
        raw_secret,
        account_name=user.email or user.get_username(),
        issuer=settings.SPECTACULAR_SETTINGS.get('TITLE', 'App'),
    )


def confirm_enrolment(user, code):
    """Activate a pending device, and issue recovery codes.

    Returns the raw recovery codes. They are shown once and only digests are
    kept, so this is the sole moment they exist outside the user's hands.
    """
    device = device_for(user)
    if device is None:
        raise TwoFactorError('Start enrolment before confirming it.')
    if device.is_confirmed:
        raise TwoFactorError('Two-factor is already enabled.')

    raw_secret = two_factor.decrypt_secret(device.encrypted_secret)
    step = two_factor.verify_code(raw_secret, code)
    if step is None:
        raise TwoFactorError(
            'That code is not correct. Check your authenticator and try again.'
        )

    device.confirmed_at = timezone.now()
    # Recording the step confirmation used means those same six digits cannot
    # then be replayed as a login within the same 30-second window. A user who
    # signs in elsewhere immediately is told to wait for the next code, which
    # is the correct answer: it is the same code.
    device.last_used_step = step
    device.save(update_fields=['confirmed_at', 'last_used_step'])

    codes = _issue_recovery_codes(user)
    audit(AuditAction.TWO_FACTOR_ENABLED, actor=user)
    return codes


def verify(user, code):
    """Check a TOTP code or a recovery code. Raises TwoFactorError if neither.

    Tries TOTP first because it is the common case; a recovery code is the
    exception and consuming one is irreversible.
    """
    device = device_for(user)
    if device is None or not device.is_confirmed:
        raise TwoFactorError('Two-factor is not enabled for this account.')

    raw_secret = two_factor.decrypt_secret(device.encrypted_secret)
    step = two_factor.verify_code(raw_secret, code)

    if step is not None:
        # A code is valid for its whole window; refusing a step at or below
        # the last accepted one stops the same code being used twice.
        if device.last_used_step is not None and step <= device.last_used_step:
            raise TwoFactorError('That code has already been used. Wait for the next one.')
        device.last_used_step = step
        device.save(update_fields=['last_used_step'])
        return 'totp'

    if _consume_recovery_code(user, code):
        return 'recovery'

    # One message for both, so the response does not say which kind of code
    # was recognised.
    raise TwoFactorError('That code is not correct.')


def disable(user):
    device = device_for(user)
    if device is None:
        raise TwoFactorError('Two-factor is not enabled for this account.')

    device.delete()
    # Recovery codes are useless without a device, and leaving them would let
    # a stale one work against a later enrolment.
    RecoveryCode.objects.filter(user=user).delete()
    audit(AuditAction.TWO_FACTOR_DISABLED, actor=user)


def regenerate_recovery_codes(user):
    if not is_required_for(user):
        raise TwoFactorError('Enable two-factor before generating recovery codes.')
    return _issue_recovery_codes(user)


def unused_recovery_code_count(user):
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


# --------------------------------------------------------------------------
# The half-finished login
# --------------------------------------------------------------------------


def begin_pending_login(request, user):
    """Remember who is halfway through logging in.

    login() is deliberately NOT called: request.user stays anonymous, so every
    IsAuthenticated view already refuses. The partial state can do nothing but
    be verified.
    """
    request.session[PENDING_SESSION_KEY] = {
        'user_id': user.pk,
        'at': timezone.now().isoformat(),
    }


def pending_user(request):
    """The user awaiting verification, or None if there is none or it expired."""
    from django.contrib.auth import get_user_model

    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        return None

    try:
        started = timezone.datetime.fromisoformat(pending['at'])
        user_id = pending['user_id']
    except (KeyError, TypeError, ValueError):
        clear_pending_login(request)
        return None

    age = (timezone.now() - started).total_seconds()
    if age > settings.TWO_FACTOR_PENDING_TIMEOUT:
        # A half-finished login left open indefinitely is a credential sitting
        # in a session cookie.
        clear_pending_login(request)
        return None

    return get_user_model().objects.filter(pk=user_id, is_active=True).first()


def clear_pending_login(request):
    request.session.pop(PENDING_SESSION_KEY, None)


def _issue_recovery_codes(user):
    RecoveryCode.objects.filter(user=user).delete()
    codes = two_factor.generate_recovery_codes()
    RecoveryCode.objects.bulk_create(
        RecoveryCode(user=user, hashed_code=two_factor.hash_recovery_code(code))
        for code in codes
    )
    return codes


def _consume_recovery_code(user, code):
    hashed = two_factor.hash_recovery_code(code)
    # Filtered on used_at, so a spent code cannot be presented twice.
    updated = RecoveryCode.objects.filter(
        user=user, hashed_code=hashed, used_at__isnull=True
    ).update(used_at=timezone.now())
    return updated == 1
