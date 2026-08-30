"""The claim this whole design rests on: MCP gets OAuth for free.

`apps/mcp_server` contains no OAuth code and imports nothing from
`apps/mcp_oauth`. It forwards the caller's `Authorization` header unchanged
into an in-process request through the full Django stack, so the moment
`BearerTokenAuthentication` is in DEFAULT_AUTHENTICATION_CLASSES, every MCP
tool accepts bearer tokens.

That is an architectural claim, and an architectural claim nobody tests is a
comment. These tests drive real tools with a real token and check what comes
back -- including the scope refusal, which is the part that would fail
silently if the two layers ever drifted apart.
"""

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings

from apps.mcp_oauth import validation

from .keys import LocalJWKS, mint, settings_ok

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        not settings.MCP_SERVER_ENABLED, reason='the MCP server is switched off'
    ),
]


@pytest.fixture(autouse=True)
def local_keys():
    validation.reset_jwks_client()
    validation._jwks_client = LocalJWKS()
    yield
    validation.reset_jwks_client()


class _As:
    """Run a block as the holder of a credential, then put it back."""

    def __init__(self, credential):
        from apps.mcp_server.credentials import set_credential

        self._set = set_credential
        self.credential = credential

    def __enter__(self):
        self.token = self._set(self.credential)
        return self

    def __exit__(self, *exc):
        from apps.mcp_server.credentials import reset_credential

        reset_credential(self.token)


def _bearer(user, scope='mcp:read mcp:write'):
    return f'Bearer {mint(sub=str(user.pk), scope=scope)}'


def test_a_tool_accepts_a_bearer_token(user):
    from apps.mcp_server.tools import identity

    with settings_ok, _As(_bearer(user)):
        data = async_to_sync(identity.whoami)()

    assert data['email'] == user.email


def test_a_tool_describes_the_tokens_owner_and_not_another_account(user, django_user_model):
    """One credential, two accounts. There is no argument a caller could pass
    to change which one a tool describes."""
    other = django_user_model.objects.create_user(
        username='mallory', email='mallory@example.com', password='hunter2hunter2'
    )
    from apps.mcp_server.tools import identity

    with settings_ok, _As(_bearer(other)):
        data = async_to_sync(identity.whoami)()

    assert data['email'] == other.email
    assert data['email'] != user.email


def test_a_read_scoped_token_is_refused_a_write_tool(user):
    """Scope is enforced once, at authentication, and the MCP layer inherits
    it -- there is no scope check anywhere in apps/mcp_server."""
    from apps.mcp_server.call import ApiError
    from apps.mcp_server.tools import records

    with settings_ok, _As(_bearer(user, scope='mcp:read')):
        with pytest.raises(ApiError) as caught:
            async_to_sync(records.update_my_profile)(first_name='Should not stick')

    assert caught.value.status in {401, 403}
    user.refresh_from_db()
    assert user.first_name != 'Should not stick'


def test_a_write_scoped_token_is_allowed_a_write_tool(user):
    """Guards the test above: the refusal must be about scope."""
    from apps.mcp_server.tools import records

    with settings_ok, _As(_bearer(user, scope='mcp:read mcp:write')):
        async_to_sync(records.update_my_profile)(first_name='Ada')

    user.refresh_from_db()
    assert user.first_name == 'Ada'


def test_a_forged_token_reaches_no_tool(user):
    """The forgeries are attacked at the validator in test_validation.py. This
    checks the refusal actually arrives here rather than being swallowed
    somewhere in the in-process request."""
    from apps.mcp_server.call import ApiError
    from apps.mcp_server.tools import identity

    forged = f'Bearer {mint(sub=str(user.pk), aud="https://elsewhere.test/")}'

    with settings_ok, _As(forged):
        with pytest.raises(ApiError) as caught:
            async_to_sync(identity.whoami)()

    assert caught.value.status in {401, 403}


def test_the_mcp_server_imports_nothing_from_the_oauth_app():
    """The independence that makes both flags removable on their own.

    If a tool ever reached for `apps.mcp_oauth` directly, MCP would stop
    working with the flag off and the two apps would no longer be separable --
    which is the thing this file exists to keep true.
    """
    import importlib.util
    import pkgutil

    import apps.mcp_server

    offenders = []
    for module in pkgutil.walk_packages(apps.mcp_server.__path__, prefix='apps.mcp_server.'):
        if '.tests' in module.name:
            continue
        # `importlib.util.find_spec` rather than `pkgutil.get_loader`, which
        # Python 3.14 removed. Reading the source without importing is the
        # point: importing every module would defeat a test about what they
        # import.
        spec = importlib.util.find_spec(module.name)
        source = spec.loader.get_source(module.name) or '' if spec and spec.loader else ''
        if 'mcp_oauth' in source:
            offenders.append(module.name)

    assert not offenders, f'apps.mcp_server must not reference apps.mcp_oauth: {offenders}'
