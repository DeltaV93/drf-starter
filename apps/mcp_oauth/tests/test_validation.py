"""Forging tokens at the validator.

This is the only security-critical code the application owns in the OAuth
story, so it is attacked rather than merely exercised. Every test below mints a
token that is wrong in exactly one way and asserts it is refused.

The happy-path test exists to keep the rest honest: without it, a validator
that rejected everything would pass every other test in this file.
"""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization

from apps.mcp_oauth.validation import ALLOWED_ALGORITHMS, InvalidToken, validate

from .keys import AUDIENCE, ISSUER, OTHER_KEY, SIGNING_KEY, LocalJWKS, mint, settings_ok


def _validate(token, key=SIGNING_KEY):
    return validate(token, jwks_client=LocalJWKS(key))


# ---------------------------------------------------------------------------
# The token that should work. Without this the rest proves nothing.
# ---------------------------------------------------------------------------


def test_a_correctly_issued_token_is_accepted():
    with settings_ok:
        claims = _validate(mint())

    assert claims.subject == 'user-123'
    assert claims.has_scope('mcp:read')
    assert claims.has_scope('mcp:write')
    assert not claims.has_scope('mcp:admin')


# ---------------------------------------------------------------------------
# The forgeries.
# ---------------------------------------------------------------------------


def test_a_token_for_a_different_audience_is_refused():
    """The check people skip, and the one that matters most.

    A token minted for another service, by the same authorization server, with
    a perfectly valid signature. Accepting it makes this application a confused
    deputy for every other service that shares the issuer.
    """
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(aud='https://someone-elses-service.test/api'))


def test_a_token_from_a_different_issuer_is_refused():
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(iss='https://attacker.example/'))


def test_a_token_signed_by_a_different_key_is_refused():
    with settings_ok:
        with pytest.raises(InvalidToken):
            # Signed with a key the JWKS does not publish.
            _validate(mint(key=OTHER_KEY))


def test_an_unsigned_token_is_refused():
    """`alg: none` — the oldest JWT attack there is.

    It works against any validator that reads the algorithm from the token
    instead of pinning it.
    """
    now = int(time.time())
    unsigned = jwt.encode(
        {
            'iss': ISSUER,
            'aud': AUDIENCE,
            'sub': 'user-123',
            'iat': now,
            'exp': now + 300,
        },
        key=None,
        algorithm=None,
    )

    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(unsigned)


def _hs256(claims, secret):
    """Mint an HS256 token by hand.

    PyJWT refuses to sign with a PEM key -- it detects the asymmetric key and
    raises. That guard belongs to the *signing* side, and an attacker mounting
    this attack is not using PyJWT; they are concatenating three base64 strings
    like this. Minting it through the library instead would test PyJWT's
    author, not this validator.
    """
    encode = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b'=')  # noqa: E731

    header = encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    payload = encode(json.dumps(claims).encode())
    signing_input = b'.'.join([header, payload])
    signature = encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    return b'.'.join([signing_input, signature]).decode()


def _attacker_claims():
    now = int(time.time())
    return {
        'iss': ISSUER,
        'aud': AUDIENCE,
        'sub': 'attacker',
        'iat': now,
        'exp': now + 300,
    }


def test_a_token_resigned_with_hmac_using_the_public_key_is_refused():
    """The RS256 to HS256 confusion attack.

    The public key is public. An attacker takes it, signs a token of their own
    choosing with HMAC using those bytes as the shared secret, and sets
    `alg: HS256`. A validator that trusts the header verifies it -- the key
    material matches -- and the attacker mints any identity they like.
    """
    public_pem = SIGNING_KEY.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(_hs256(_attacker_claims(), public_pem))


def test_the_hmac_forgery_is_a_token_a_header_trusting_validator_would_accept():
    """Guards the test above, which is the one that could pass for free.

    A refusal proves nothing if the forged token was malformed to begin with.
    So the same attack is mounted with the key in DER rather than PEM -- the
    one form PyJWT will accept as an HMAC secret -- and PyJWT is asked to
    verify it while trusting the header. It does, which is precisely the
    failure mode. Our validator, pinning the algorithm instead, refuses it.
    """
    public_der = SIGNING_KEY.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    forged = _hs256(_attacker_claims(), public_der)

    # A header-trusting validator: the algorithm comes from the token.
    accepted = jwt.decode(
        forged, public_der, algorithms=['HS256'], audience=AUDIENCE, issuer=ISSUER
    )
    assert accepted['sub'] == 'attacker'

    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(forged)


def test_an_expired_token_is_refused():
    now = int(time.time())
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(exp=now - 1, iat=now - 600))


def test_a_token_not_yet_valid_is_refused():
    now = int(time.time())
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(nbf=now + 600))


@pytest.mark.parametrize('claim', ['exp', 'iat', 'sub', 'aud', 'iss'])
def test_a_token_missing_a_required_claim_is_refused(claim):
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(**{claim: None}))


def test_a_token_with_an_empty_subject_is_refused():
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate(mint(sub=''))


def test_garbage_is_refused_without_raising_something_else():
    with settings_ok:
        with pytest.raises(InvalidToken):
            _validate('not-a-token')


# ---------------------------------------------------------------------------
# The configuration itself.
# ---------------------------------------------------------------------------


def test_only_asymmetric_algorithms_are_accepted():
    """A symmetric algorithm would mean this application holding the key that
    signs tokens, which is the authorization server's job — and it is the
    pairing the confusion attack above depends on."""
    assert not [a for a in ALLOWED_ALGORITHMS if a.startswith('HS')]
    assert all(a.startswith(('RS', 'ES')) for a in ALLOWED_ALGORITHMS)


def test_scopes_are_read_from_either_claim_name():
    """RFC 8693 says `scope`; several servers emit `scp`. Refusing a correctly
    issued token over a claim-name convention would be a bug, not rigour."""
    with settings_ok:
        from_scp = _validate(mint(scope=None, scp=['mcp:read']))
        from_list = _validate(mint(scope=None, scp='mcp:read mcp:write'))

    assert from_scp.has_scope('mcp:read')
    assert from_list.has_scope('mcp:write')
