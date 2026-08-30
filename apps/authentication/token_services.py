"""Issuing, refreshing and revoking the mobile client's bearer tokens.

Kept out of the views for the same reason `two_factor_services` is: the rules
about what a token means are worth reading without a request object in the
way, and the two-factor flow needs to issue a pair from a second endpoint.
"""

import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core import signing
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Namespaces the signature, so a challenge cannot be replayed at any other
# place in the project that happens to sign a user id.
CHALLENGE_SALT = 'apps.authentication.token_services.two_factor_challenge'


class TokenServiceError(Exception):
    """A token could not be issued, refreshed or revoked."""


def issue_pair(user):
    """Mint a fresh access/refresh pair for a user who has proved who they are.

    Callers are responsible for that proof. Nothing here checks a password.
    """
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    if settings.SIMPLE_JWT.get('UPDATE_LAST_LOGIN'):
        update_last_login(None, user)

    return {
        'access': str(access),
        'refresh': str(refresh),
        # Seconds rather than an absolute time: a phone's clock can be wrong,
        # and the client only needs this to refresh before it is turned away.
        'access_expires_in': int(access.lifetime.total_seconds()),
    }


def refresh_pair(raw_refresh):
    """Spend a refresh token and get a new pair.

    Rotation is on, so the token presented here is blacklisted in the same
    breath. Presenting it twice fails the second time -- which is the only
    signal the server ever gets that a refresh token leaked.
    """
    try:
        refresh = RefreshToken(raw_refresh)
    except TokenError as exc:
        raise TokenServiceError('That session has expired. Please sign in again.') from exc

    try:
        refresh.blacklist()
    except AttributeError as exc:  # pragma: no cover - the app is always installed
        raise TokenServiceError('Token revocation is not configured.') from exc

    user = _user_for(refresh)
    if user is None:
        raise TokenServiceError('That session is no longer valid. Please sign in again.')

    return issue_pair(user)


def revoke(raw_refresh):
    """Blacklist a refresh token. This is what "log out" means on mobile.

    The access token already issued stays valid until it expires -- nothing
    consults a database on the way through, which is the trade that makes it
    cheap. Keep ACCESS_TOKEN_LIFETIME short and that window stays small.
    """
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError as exc:
        # Already expired, already blacklisted, or never valid. Logging out
        # twice is not an error worth reporting to someone tapping a button.
        raise TokenServiceError('That session was already ended.') from exc


def _user_for(refresh):
    identifier = refresh.payload.get('user_id')
    if identifier is None:
        return None
    return User.objects.filter(pk=identifier, is_active=True).first()


# ---------------------------------------------------------------------------
# The two-factor challenge
#
# The session flow parks a pending login in the session and lets the cookie
# carry it to the verify request. A token client has no session, so the
# pending state has to travel in the response instead -- signed, so the client
# cannot promote itself past the second factor by editing it.
# ---------------------------------------------------------------------------


def issue_challenge(user):
    """A short-lived, signed marker that this user's password was accepted."""
    return signing.dumps(
        {'uid': user.pk, 'pwd': _password_fingerprint(user)},
        salt=CHALLENGE_SALT,
    )


def user_for_challenge(raw_challenge):
    """The user a challenge stands for, or None if it is not redeemable.

    None covers every failure alike -- forged, expired, or superseded by a
    password change -- because telling them apart tells an attacker which of
    their guesses was closest.
    """
    try:
        payload = signing.loads(
            raw_challenge,
            salt=CHALLENGE_SALT,
            max_age=settings.TOKEN_TWO_FACTOR_CHALLENGE_SECONDS,
        )
    except (signing.BadSignature, signing.SignatureExpired):
        return None

    user = User.objects.filter(pk=payload.get('uid'), is_active=True).first()
    if user is None:
        return None

    # A password change mid-challenge invalidates it. Without this, a
    # challenge minted with the old password stays redeemable for its full
    # window after the owner has reacted to a compromise by changing it.
    if payload.get('pwd') != _password_fingerprint(user):
        return None

    return user


def _password_fingerprint(user):
    """A short digest of the stored password hash.

    Of the hash, never of the password: this value goes out to the client
    inside the challenge, and a hash of a hash leaks nothing usable.
    """
    return hashlib.sha256(user.password.encode()).hexdigest()[:16]
