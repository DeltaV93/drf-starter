"""Error tracking is presence-gated, and never armed during a test run.

Sentry is turned on by SENTRY_DSN alone -- there is no separate flag, and
nothing is imported without it. The case worth pinning is the negative: a CI
machine with a DSN in its environment must not fill a real project with noise
from tests that fail on purpose.

These patch sentry_sdk.init and assert on what base.py passes it. An earlier
version let the real init run, which armed a client that then tried to POST to
sentry.io from the test suite -- proving the point at the cost of the run.
"""

import importlib
import sys
from unittest.mock import patch

import pytest

DSN = 'https://public@o0.ingest.sentry.io/0'

SENTRY_ENV_KEYS = (
    'SENTRY_DSN',
    'SENTRY_TRACES_SAMPLE_RATE',
    'SENTRY_SEND_PII',
    'SENTRY_RELEASE',
    'RAILWAY_GIT_COMMIT_SHA',
    'RENDER_GIT_COMMIT',
)


@pytest.fixture
def load_base(monkeypatch):
    """Re-import base.py under `env`, returning the captured sentry_sdk.init mock."""
    original = sys.modules.get('clearpath.settings.base')

    def _load(env):
        for key in SENTRY_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        # base.py refuses to generate one outside development and testing, and
        # several cases below deliberately claim to be production.
        monkeypatch.setenv('SECRET_KEY', 'test-key-not-used-outside-the-suite-0000')
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        sys.modules.pop('clearpath.settings.base', None)
        with patch('sentry_sdk.init') as init:
            importlib.import_module('clearpath.settings.base')
        return init

    yield _load

    sys.modules.pop('clearpath.settings.base', None)
    if original is not None:
        sys.modules['clearpath.settings.base'] = original


def test_the_settings_module_reports_the_testing_environment():
    """Everything below depends on this being right.

    DJANGO_SETTINGS_MODULE points straight at testing.py when the suite runs,
    which leaves DJANGO_ENVIRONMENT unset -- base.py would call it
    'development', and the guard in the next test would never fire.
    """
    from django.conf import settings

    assert settings.ENVIRONMENT == 'testing'


def test_sentry_is_not_initialised_during_a_test_run(load_base):
    init = load_base({'SENTRY_DSN': DSN, 'DJANGO_ENVIRONMENT': 'testing'})

    init.assert_not_called()


def test_no_dsn_means_no_initialisation(load_base):
    init = load_base({'DJANGO_ENVIRONMENT': 'production'})

    init.assert_not_called()


def test_a_dsn_outside_testing_initialises(load_base):
    init = load_base({'SENTRY_DSN': DSN, 'DJANGO_ENVIRONMENT': 'production'})

    init.assert_called_once()
    assert init.call_args.kwargs['dsn'] == DSN
    assert init.call_args.kwargs['environment'] == 'production'


def test_pii_is_off_unless_asked_for(load_base):
    """Turning it on ships emails, usernames and IP addresses to a third party."""
    init = load_base({'SENTRY_DSN': DSN, 'DJANGO_ENVIRONMENT': 'production'})

    assert init.call_args.kwargs['send_default_pii'] is False


def test_pii_can_be_turned_on_deliberately(load_base):
    init = load_base(
        {
            'SENTRY_DSN': DSN,
            'DJANGO_ENVIRONMENT': 'production',
            'SENTRY_SEND_PII': 'true',
        }
    )

    assert init.call_args.kwargs['send_default_pii'] is True


def test_tracing_is_off_by_default(load_base):
    """Sampling costs money and quota; opting in should be explicit."""
    init = load_base({'SENTRY_DSN': DSN, 'DJANGO_ENVIRONMENT': 'production'})

    assert init.call_args.kwargs['traces_sample_rate'] == 0.0


def test_the_release_comes_from_the_platform(load_base):
    """A release makes a traceback point at a commit, not at 'production'."""
    init = load_base(
        {
            'SENTRY_DSN': DSN,
            'DJANGO_ENVIRONMENT': 'production',
            'RAILWAY_GIT_COMMIT_SHA': 'deadbeef',
        }
    )

    assert init.call_args.kwargs['release'] == 'deadbeef'


def test_an_explicit_release_wins(load_base):
    init = load_base(
        {
            'SENTRY_DSN': DSN,
            'DJANGO_ENVIRONMENT': 'production',
            'RAILWAY_GIT_COMMIT_SHA': 'deadbeef',
            'SENTRY_RELEASE': 'v1.2.3',
        }
    )

    assert init.call_args.kwargs['release'] == 'v1.2.3'


def test_no_release_information_is_not_an_error(load_base):
    init = load_base({'SENTRY_DSN': DSN, 'DJANGO_ENVIRONMENT': 'production'})

    assert init.call_args.kwargs['release'] is None
