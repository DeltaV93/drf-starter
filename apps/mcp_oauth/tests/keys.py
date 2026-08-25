"""Minting tokens for the tests, without an authorization server.

Every token in this suite is signed by a key generated here and verified
against a key set supplied here. Nothing reaches the network, and nothing
depends on Hydra being up -- which is what makes the security tests runnable
in CI rather than by hand.
"""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings

ISSUER = 'https://auth.example.test/'
AUDIENCE = 'https://app.example.test/mcp'

# Generated once for the module: RSA keygen is slow and it is not what is
# being measured. SIGNING_KEY is the one the fake JWKS publishes; OTHER_KEY is
# one it does not, for the wrong-key test.
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class LocalJWKS:
    """Stands in for the authorization server's key endpoint.

    Injected rather than mocked over the network, so these tests never depend
    on reaching anything. Everything downstream of it -- signature check,
    audience, issuer, expiry, algorithm pinning -- is the real code.
    """

    def __init__(self, key=SIGNING_KEY):
        self._key = key

    def get_signing_key_from_jwt(self, token):
        class _Key:
            key = self._key.public_key()
            algorithm_name = 'RS256'

        return _Key()


def mint(key=SIGNING_KEY, algorithm='RS256', **overrides):
    """A well-formed token, with any claim overridden or removed.

    Passing a claim as None removes it, which is how the missing-claim tests
    are written.
    """
    now = int(time.time())
    claims = {
        'iss': ISSUER,
        'aud': AUDIENCE,
        'sub': 'user-123',
        'iat': now,
        'exp': now + 300,
        'scope': 'mcp:read mcp:write',
    }
    claims.update(overrides)
    for name in [k for k, v in overrides.items() if v is None]:
        claims.pop(name, None)
    return jwt.encode(claims, key, algorithm=algorithm)


settings_ok = override_settings(
    MCP_OAUTH_ISSUER=ISSUER,
    MCP_OAUTH_AUDIENCE=AUDIENCE,
    MCP_OAUTH_JWKS_URL='https://auth.example.test/.well-known/jwks.json',
    MCP_OAUTH_JWKS_CACHE_SECONDS=300,
    MCP_OAUTH_SUBJECT_CLAIM='sub',
    MCP_OAUTH_USER_LOOKUP_FIELD='pk',
    MCP_OAUTH_WRITE_SCOPE='mcp:write',
)
