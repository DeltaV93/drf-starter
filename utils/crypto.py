"""Encrypting a bearer credential at rest.

Used wherever the database stores something that is itself enough to act as
somebody: a TOTP secret, an OAuth token for a third-party server. A database
dump alone should not hand an attacker a working credential.

Fernet over a key derived from settings material. The derivation is a plain
SHA-256 of the configured string, so any string works as key material and
there is nothing extra to generate or rotate on first deploy.

**The rotation trade-off is the thing to understand before using this.** The
key material usually falls back to `SECRET_KEY`, which means rotating
`SECRET_KEY` makes every stored value undecryptable. For a TOTP secret that
locks enrolled users out of their own accounts; for a stored OAuth token it
means every connection has to be re-authorised. Set the feature's own key
setting explicitly before you ever need to rotate.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def fernet_for(material: str) -> Fernet:
    """A Fernet keyed on arbitrary settings material."""
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest()))


def encrypt(value: str, material: str) -> str:
    return fernet_for(material).encrypt(value.encode()).decode()


def decrypt(stored: str, material: str) -> str | None:
    """The plaintext, or None if it cannot be decrypted.

    None rather than an exception, because every caller here has to fail
    closed: a decryption problem must never be mistaken for a valid
    credential, and a helpful error is worth less than a refusal.
    """
    try:
        return fernet_for(material).decrypt(stored.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return None
