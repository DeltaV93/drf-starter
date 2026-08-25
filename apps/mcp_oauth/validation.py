"""Validating an OAuth access token.

This is the only security-critical code in the OAuth story, and it is
deliberately small. Everything genuinely dangerous — the authorize endpoint,
consent, code exchange, PKCE, redirect-URI matching, token issuance, key
rotation — lives in the authorization server, which is not this. RFC 9728
formalises that split and MCP's auth spec adopts it: this application is a
*resource server*, and it publishes where its authorization server is rather
than being one.

So there is no OAuth library here beyond JWT verification, and no new
dependency: `PyJWT` and `cryptography` are already installed.

## What has to be checked, and why each one matters

Every line below is load-bearing. In rough order of how often it is the one
people skip:

**`aud` — the audience.** A token minted for a *different* resource must be
refused. Without this check, any service that shares an authorization server
can hand this one a token it was given for itself and act as its bearer. That
is the confused-deputy attack, and MCP's spec names it explicitly as the reason
a server must validate the audience.

**The algorithm.** Pinned to an allow-list here, never read from the token's
own header. Trusting the header is how `alg: none` works, and how the RS256 →
HS256 confusion attack works: an attacker re-signs the token with HMAC using
the *public* key as the shared secret, and a validator that believes the header
verifies it happily.

**`iss` — the issuer.** Exactly the configured authorization server. A validly
signed token from somewhere else is somebody else's token.

**`exp` / `nbf`.** Ordinary expiry, enforced by PyJWT once required.

**The key set.** Fetched over TLS from the authorization server's JWKS
endpoint and cached with a bounded lifetime, so key rotation is picked up
without a restart and a poisoned cache cannot persist.

None of this is novel. It is written out because the failure mode of getting it
wrong is silent: a validator that skips the audience check accepts every token
it is given and looks like it is working perfectly.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from django.conf import settings
from jwt import PyJWKClient

# Asymmetric only. A symmetric algorithm would mean this application holding
# the key that signs tokens, which is the authorization server's job -- and it
# is the pairing that makes the RS256 -> HS256 confusion attack possible.
ALLOWED_ALGORITHMS = ('RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512')


class InvalidToken(Exception):
    """The token is not acceptable, for any reason.

    One exception rather than several on purpose: an expired token, a token for
    another audience and a forged signature must be indistinguishable from
    outside, or the difference becomes an oracle.
    """


@dataclass(frozen=True)
class TokenClaims:
    """The parts of a verified token this application acts on."""

    subject: str
    scopes: frozenset[str]
    raw: dict

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


_jwks_client: PyJWKClient | None = None


def _client() -> PyJWKClient:
    """The JWKS client, built once and cached.

    `lifespan` bounds how long a key set is trusted, so a rotation is picked up
    without a restart. Rebuilding per request would fetch the key set on every
    call and make the authorization server a hard dependency of every request.
    """
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.MCP_OAUTH_JWKS_URL,
            cache_keys=True,
            lifespan=settings.MCP_OAUTH_JWKS_CACHE_SECONDS,
        )
    return _jwks_client


def reset_jwks_client() -> None:
    """Drop the cached client. For tests, and for a deliberate key refresh."""
    global _jwks_client
    _jwks_client = None


def _scopes_from(claims: dict) -> frozenset[str]:
    """Scopes, from whichever claim the authorization server uses.

    RFC 8693 says `scope`, space-delimited. Several servers emit `scp` instead,
    sometimes as a list. Reading both is not laxity -- refusing a correctly
    issued token because of a claim-name convention would be.
    """
    raw = claims.get('scope') or claims.get('scp') or ''
    if isinstance(raw, str):
        return frozenset(raw.split())
    if isinstance(raw, (list, tuple)):
        return frozenset(str(item) for item in raw)
    return frozenset()


def validate(token: str, *, jwks_client: PyJWKClient | None = None) -> TokenClaims:
    """Verify a bearer token, or raise `InvalidToken`.

    `jwks_client` is injectable so tests can supply a local key set rather than
    reaching the network. Production passes nothing.
    """
    client = jwks_client or _client()

    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except Exception as exc:
        # Covers an unknown `kid`, an unreachable JWKS endpoint and a malformed
        # token alike. The caller learns none of that.
        raise InvalidToken('Could not find a key for this token.') from exc

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            # Never `signing_key.algorithm_name` and never the token's own
            # header -- both let the token choose how it is verified.
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=settings.MCP_OAUTH_AUDIENCE,
            issuer=settings.MCP_OAUTH_ISSUER,
            options={
                'require': ['exp', 'iat', 'sub', 'aud', 'iss'],
                'verify_signature': True,
                'verify_exp': True,
                'verify_nbf': True,
                'verify_aud': True,
                'verify_iss': True,
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    subject = claims.get('sub')
    if not subject:
        raise InvalidToken('The token has no subject.')

    return TokenClaims(
        subject=str(subject),
        scopes=_scopes_from(claims),
        raw=claims,
    )
