"""What production actually refuses to start without.

`docs/getting-started.md` opens by promising that production needs exactly
four variables and development needs none. That is the single most useful
sentence in the documentation and the easiest one to quietly falsify: adding a
fifth required setting is a one-line change in `production.py`, and nothing
about it looks like a documentation change.

So the claim is asserted here rather than written down and hoped for. Each
test boots a real settings module in a subprocess with a controlled
environment -- `django.setup()` in-process would inherit this one and can only
happen once.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[3]

# The four the guide names. Kept as a literal, so changing the requirement
# means changing this list -- and noticing the document that quotes it.
REQUIRED_IN_PRODUCTION = {
    'SECRET_KEY': 'x' * 50,
    'ALLOWED_HOSTS': 'example.com',
    'DATABASE_URL': 'postgres://user:pass@db.example.com:5432/name',
    'FRONTEND_URL': 'https://example.com',
}

GUIDE = BASE_DIR / 'docs' / 'getting-started.md'


def _boot(environment):
    """Import a settings module in a clean subprocess.

    Returns (started, last line of stderr). Nothing connects to a database --
    `django.setup()` only reads configuration.
    """
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', '/tmp'),
        'PYTHONPATH': str(BASE_DIR),
        'DJANGO_SETTINGS_MODULE': 'template.settings',
        **environment,
    }
    result = subprocess.run(
        [sys.executable, '-c', 'import django; django.setup()'],
        capture_output=True,
        text=True,
        env=env,
        cwd=BASE_DIR,
        timeout=120,
    )
    stderr = result.stderr.strip().splitlines()
    return result.returncode == 0, (stderr[-1] if stderr else '')


def test_development_needs_no_configuration_at_all():
    """The claim the quick start rests on.

    A contributor clones, runs `make up`, and edits nothing. If some setting
    ever becomes required in development, that stops being true and the first
    person to find out is whoever is following the README.
    """
    started, error = _boot({'DJANGO_ENVIRONMENT': 'development'})

    assert started, f'development should boot with an empty environment: {error}'


def test_production_starts_with_exactly_the_documented_four():
    started, error = _boot({'DJANGO_ENVIRONMENT': 'production', **REQUIRED_IN_PRODUCTION})

    assert started, f'production should boot with the documented four: {error}'


@pytest.mark.parametrize('missing', sorted(REQUIRED_IN_PRODUCTION))
def test_production_refuses_without_each_one_and_names_it(missing):
    """Refusing is half of it; saying which variable is the other half.

    Each of these fails silently and much later if it defaults to something
    plausible -- a shared SECRET_KEY, a localhost database, a password reset
    link pointing at someone's laptop. The error has to name the variable, or
    the reader is left debugging the symptom.
    """
    environment = {
        'DJANGO_ENVIRONMENT': 'production',
        **{k: v for k, v in REQUIRED_IN_PRODUCTION.items() if k != missing},
    }
    started, error = _boot(environment)

    assert not started, f'production booted without {missing}'
    assert missing in error, f'the error for a missing {missing} does not name it: {error}'


def test_a_platform_domain_supplies_two_of_the_four():
    """Railway, Render and Fly expose their domain only after the first
    deploy, so requiring it up front would make that deploy crash. The guide
    tells people they need two variables on those platforms; this is why."""
    started, error = _boot(
        {
            'DJANGO_ENVIRONMENT': 'production',
            'RAILWAY_PUBLIC_DOMAIN': 'myapp.up.railway.app',
            'SECRET_KEY': REQUIRED_IN_PRODUCTION['SECRET_KEY'],
            'DATABASE_URL': REQUIRED_IN_PRODUCTION['DATABASE_URL'],
        }
    )

    assert started, f'a platform-supplied domain should cover the other two: {error}'


def test_the_guide_names_the_same_four():
    """Pins the prose to the code.

    Without this the tests above could stay green while the document drifted
    into naming a fifth variable, or dropping one.
    """
    text = GUIDE.read_text()
    # The heading itself, not the table-of-contents link to it.
    heading = '\n## The four variables production needs\n'

    assert heading in text, f'{GUIDE.name} no longer has the section this test pins'

    section = text.split(heading, 1)[1].split('\n## ', 1)[0]
    for name in REQUIRED_IN_PRODUCTION:
        assert f'`{name}`' in section, f'{GUIDE.name} does not name {name}'
