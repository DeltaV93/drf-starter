"""TOTP two-factor: secrets, codes and recovery.

The model lives in this always-installed app rather than in one of its own, so
the table exists whether or not TWO_FACTOR_ENABLED is set. An empty table costs
nothing, and it avoids a migration that appears and disappears with a flag.

The secret is encrypted at rest. A TOTP secret is a bearer credential: anyone
holding it can generate valid codes forever, so a database dump alone should
not be enough. See ENCRYPTION NOTE below for the key-rotation trade-off that
buys.
"""

import base64
import hashlib
import secrets

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

# How many 30-second steps either side of now are accepted, to tolerate a
# phone whose clock has drifted. One step each way is the usual compromise:
# more widens the window an intercepted code stays usable in.
VALID_WINDOW = 1

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 5  # 10 hex characters, shown in two groups of five.


def _fernet():
    """Derive the encryption key.

    ENCRYPTION NOTE: TWO_FACTOR_SECRET_KEY falls back to SECRET_KEY, which
    means rotating SECRET_KEY makes every enrolled secret undecryptable and
    locks those users out of their own accounts -- worse than the session
    invalidation rotation already causes. Set TWO_FACTOR_SECRET_KEY explicitly
    before you ever need to rotate.
    """
    material = getattr(settings, 'TWO_FACTOR_SECRET_KEY', '') or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest()))


def encrypt_secret(raw_secret):
    return _fernet().encrypt(raw_secret.encode()).decode()


def decrypt_secret(stored_secret):
    """Return the raw secret, or None if it cannot be decrypted.

    None makes verification fail. Failing closed matters more here than a
    helpful error: a decryption problem must never be mistaken for a valid
    code.
    """
    try:
        return _fernet().decrypt(stored_secret.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return None


def generate_secret():
    return pyotp.random_base32()


def provisioning_uri(raw_secret, account_name, issuer):
    """The otpauth:// URI an authenticator app scans."""
    return pyotp.TOTP(raw_secret).provisioning_uri(name=account_name, issuer_name=issuer)


def verify_code(raw_secret, code):
    """Check a TOTP code, returning the step it matched or None.

    The step is returned so the caller can refuse a code that has already been
    used: without that, a code stays replayable for its whole validity window,
    which is exactly long enough for someone reading it over a shoulder or off
    a proxy log.
    """
    if not raw_secret or not code:
        return None

    code = code.strip().replace(' ', '')
    if not code.isdigit():
        return None

    totp = pyotp.TOTP(raw_secret)
    now = totp.timecode(_now())
    for offset in range(-VALID_WINDOW, VALID_WINDOW + 1):
        step = now + offset
        # compare_digest: the comparison must not leak how much of the code
        # was correct.
        if secrets.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def _now():
    import datetime

    return datetime.datetime.now(datetime.UTC)


def generate_recovery_codes(count=RECOVERY_CODE_COUNT):
    """Fresh single-use codes. Returned raw; only digests are stored."""
    return [secrets.token_hex(RECOVERY_CODE_BYTES) for _ in range(count)]


def hash_recovery_code(code):
    """Digest a recovery code.

    SHA-256 rather than a password hash: the code is random, so there is
    nothing to brute-force, and normalising here means the user can type it
    with or without the spaces it was displayed with.
    """
    return hashlib.sha256(normalise_recovery_code(code).encode()).hexdigest()


def normalise_recovery_code(code):
    return (code or '').strip().lower().replace(' ', '').replace('-', '')
