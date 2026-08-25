"""The published OpenAPI schema.

CI runs `manage.py spectacular --fail-on-warn`, which turns any undocumented
view into a failed build. That check is a wall, not a description: it says
something is wrong without saying what should have been there. These tests
name the parts of the schema that carry meaning, so losing one fails with a
sentence rather than a warning count.
"""

import pytest
from django.conf import settings
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture
def schema(db):
    return SchemaGenerator().get_schema(request=None, public=True)


def test_the_schema_generates_without_errors(schema):
    assert schema['openapi'].startswith('3.')
    assert schema['paths']


@pytest.mark.skipif(not settings.API_KEYS_ENABLED, reason='API keys are switched off')
def test_api_key_authentication_appears_as_a_security_scheme(schema):
    """Without the extension in apps/api_keys/schema.py the generator drops
    this and documents cookies as the only credential -- while the README
    hands out a curl command that uses a key."""
    schemes = schema['components']['securitySchemes']

    assert 'apiKeyAuth' in schemes, f'expected an API-key scheme, got {sorted(schemes)}'
    assert schemes['apiKeyAuth']['scheme'] == 'api-key'


@pytest.mark.skipif(not settings.MCP_OAUTH_ENABLED, reason='MCP OAuth is switched off')
def test_bearer_authentication_appears_as_a_security_scheme(schema):
    """Without the extension in apps/mcp_oauth/schema.py the generator drops
    this with a warning on every view, and --fail-on-warn fails the build."""
    schemes = schema['components']['securitySchemes']

    assert 'oauth2Bearer' in schemes, f'expected a bearer scheme, got {sorted(schemes)}'
    assert schemes['oauth2Bearer']['scheme'] == 'bearer'


@pytest.mark.skipif(not settings.MCP_OAUTH_ENABLED, reason='MCP OAuth is switched off')
def test_the_metadata_endpoint_is_documented_as_needing_no_credential(schema):
    """A client reads it *before* it has a token. Documenting it as
    authenticated would tell an integrator the opposite of the truth."""
    path = schema['paths']['/.well-known/oauth-protected-resource']['get']

    # `[{}]` is OpenAPI for "one acceptable option: no credential". An
    # absent key would mean "inherit the global requirement", which reads
    # the same only while there is no global one.
    assert path['security'] == [{}]


@pytest.mark.skipif(not settings.API_KEYS_ENABLED, reason='API keys are switched off')
def test_the_creation_response_is_the_only_one_carrying_the_secret(schema):
    components = schema['components']['schemas']

    assert 'key' in components['CreatedAPIKey']['properties']
    assert 'key' not in components['APIKey']['properties']


@pytest.mark.skipif(
    not settings.ORGANIZATIONS_ENABLED, reason='organizations are switched off'
)
def test_the_two_role_enums_are_named_apart(schema):
    """`CustomUser.role` is product-wide and `Membership.role` is per
    organization -- the distinction the whole B2B shape rests on. Left to
    resolve the clash itself the generator emits a hashed name like
    `Role6d0Enum`, which reads as a bug in the API rather than a decision."""
    components = schema['components']['schemas']

    assert 'UserRoleEnum' in components
    assert 'MembershipRoleEnum' in components
    assert not [name for name in components if name.startswith('Role') and 'Enum' in name]
