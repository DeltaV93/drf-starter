"""Configuration documentation matches the code that reads it.

A configuration reference rots quietly. Someone adds a setting, the feature
works, the tests pass, and the variable simply has no documented existence --
until the next person deploys without it and finds out what the default was.
Nothing fails, so nothing gets fixed.

These tests are the thing that fails. `scripts/env_vars.py` parses the source
for every environment read; the assertions below compare that against
`.env.example`, `website/.env.example`, `mobile/.env.example` and
`docs/configuration.md`, in both directions, and name what is missing.

Not settings-dependent, so they run under every flag combination -- which
matters, because a variable read inside `if UPLOADS_ENABLED:` is still a
variable someone has to know about.
"""

import pytest

from scripts.env_vars import (
    BASE_DIR,
    _names_in_env_file,
    backend_settings,
    documentable,
    documented_in_reference,
    frontend_settings,
    mobile_settings,
    settings_read,
)


def _listing(names):
    return '\n  '.join(sorted(names))


def test_every_backend_setting_is_in_env_example():
    documented = _names_in_env_file(BASE_DIR / '.env.example')
    missing = backend_settings() - documented

    assert not missing, (
        'Read by the code but absent from .env.example:\n  '
        f'{_listing(missing)}\n'
        'Add each one, with a comment saying what it does.'
    )


def test_every_frontend_setting_is_in_the_website_env_example():
    documented = _names_in_env_file(BASE_DIR / 'website' / '.env.example')
    missing = frontend_settings() - documented

    assert not missing, (
        'Read by the SPA or its build but absent from website/.env.example:\n  '
        f'{_listing(missing)}'
    )


def test_every_mobile_setting_is_in_the_mobile_env_example():
    documented = _names_in_env_file(BASE_DIR / 'mobile' / '.env.example')
    missing = mobile_settings() - documented

    assert not missing, (
        f'Read by the mobile app but absent from mobile/.env.example:\n  {_listing(missing)}'
    )


def test_env_example_does_not_invent_settings():
    documented = (
        _names_in_env_file(BASE_DIR / '.env.example')
        | _names_in_env_file(BASE_DIR / 'website' / '.env.example')
        | _names_in_env_file(BASE_DIR / 'mobile' / '.env.example')
    )
    extra = documented - settings_read()

    # The other direction, and the more embarrassing one: a variable someone
    # sets in production, believing the file, that nothing has read since it
    # was renamed.
    assert not extra, (
        'Listed in a .env.example but read by nothing:\n  '
        f'{_listing(extra)}\n'
        'Either the code stopped reading it, or it was renamed.'
    )


def test_every_setting_is_in_the_configuration_reference():
    missing = settings_read() - documented_in_reference()

    assert not missing, (
        'Read by the code but absent from docs/configuration.md:\n  '
        f'{_listing(missing)}\n'
        'Add a table row: | `NAME` | default | what it does |'
    )


def test_the_configuration_reference_does_not_invent_settings():
    extra = documented_in_reference() - documentable()

    assert not extra, (
        f'Listed in docs/configuration.md but read by nothing:\n  {_listing(extra)}'
    )


@pytest.mark.parametrize(
    'flag',
    [
        'STRIPE_ENABLED',
        'SOCIAL_AUTH_ENABLED',
        'ORGANIZATIONS_ENABLED',
        'API_KEYS_ENABLED',
        'AUDIT_LOG_ENABLED',
        'TWO_FACTOR_ENABLED',
        'UPLOADS_ENABLED',
    ],
)
def test_each_backend_flag_has_a_frontend_twin(flag):
    """A flag with no VITE_ counterpart gates an API nothing can reach.

    The pairing is a convention, not something the code enforces -- the two
    halves are read in different languages at different times. This is what
    keeps a new feature from shipping with a backend-only flag, which is
    exactly how the previous six features shipped.
    """
    twin = f'VITE_{flag}'
    assert twin in frontend_settings(), (
        f'{flag} gates the backend but nothing reads {twin}. Add it to '
        'website/.env.example, the Dockerfile build args, and the component '
        'that should disappear when the feature is off.'
    )
