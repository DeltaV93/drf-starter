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


def _check(environment):
    """Run `manage.py check` and return (passed, combined output).

    The scheme and trailing-slash rules below are enforced by Django's and
    django-cors-headers' own checks rather than by anything in this project,
    which is exactly why they are worth pinning: an upgrade could change the
    codes or drop a check, and the guide quotes them verbatim.
    """
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', '/tmp'),
        'PYTHONPATH': str(BASE_DIR),
        'DJANGO_SETTINGS_MODULE': 'clearpath.settings',
        'DJANGO_ENVIRONMENT': 'production',
        **REQUIRED_IN_PRODUCTION,
        **environment,
    }
    result = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        capture_output=True,
        text=True,
        env=env,
        cwd=BASE_DIR,
        timeout=120,
    )
    return result.returncode == 0, result.stdout + result.stderr


def _boot(environment):
    """Import a settings module in a clean subprocess.

    Returns (started, last line of stderr). Nothing connects to a database --
    `django.setup()` only reads configuration.
    """
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', '/tmp'),
        'PYTHONPATH': str(BASE_DIR),
        'DJANGO_SETTINGS_MODULE': 'clearpath.settings',
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


# ---------------------------------------------------------------------------
# FRONTEND_URL, which fails in three places and names itself in none of them.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('value', ['https://example.com', 'http://example.com'])
def test_a_frontend_url_with_a_scheme_and_no_trailing_slash_passes(value):
    passed, output = _check({'FRONTEND_URL': value})

    assert passed, output


def test_a_frontend_url_without_a_scheme_is_refused():
    """Two checks catch this, and the guide quotes both codes."""
    passed, output = _check({'FRONTEND_URL': 'example.com'})

    assert not passed
    assert 'corsheaders.E013' in output, output
    assert '4_0.E001' in output, output


def test_a_frontend_url_with_a_trailing_slash_is_refused():
    passed, output = _check({'FRONTEND_URL': 'https://example.com/'})

    assert not passed
    assert 'corsheaders.E014' in output, output


# ---------------------------------------------------------------------------
# DATABASE_URL, and the shapes that cannot connect.
# ---------------------------------------------------------------------------


def _database(environment):
    """The resolved default database, as settings see it."""
    import json

    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', '/tmp'),
        'PYTHONPATH': str(BASE_DIR),
        'DJANGO_SETTINGS_MODULE': 'clearpath.settings',
        'DJANGO_ENVIRONMENT': 'production',
        'SECRET_KEY': REQUIRED_IN_PRODUCTION['SECRET_KEY'],
        'ALLOWED_HOSTS': REQUIRED_IN_PRODUCTION['ALLOWED_HOSTS'],
        'FRONTEND_URL': REQUIRED_IN_PRODUCTION['FRONTEND_URL'],
        **environment,
    }
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'import django, json; django.setup()\n'
            'from django.conf import settings\n'
            'd = settings.DATABASES["default"]\n'
            'print(json.dumps({"host": d.get("HOST"), "name": d.get("NAME"), '
            '"sslmode": (d.get("OPTIONS") or {}).get("sslmode")}))',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=BASE_DIR,
        timeout=120,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout.strip())


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql'])
def test_both_url_schemes_are_accepted(scheme):
    """Providers are inconsistent about which they hand out."""
    resolved = _database({'DATABASE_URL': f'{scheme}://u:p@db.example.com:5432/mydb'})

    assert resolved == {'host': 'db.example.com', 'name': 'mydb', 'sslmode': 'require'}


def test_a_remote_database_requires_tls_and_a_local_one_does_not():
    remote = _database({'DATABASE_URL': 'postgres://u:p@db.example.com:5432/mydb'})
    local = _database({'DATABASE_URL': 'postgres://u:p@localhost:5432/mydb'})

    assert remote['sslmode'] == 'require'
    assert local['sslmode'] is None, 'a compose Postgres has no certificate to verify'


def test_an_sslmode_query_parameter_does_not_override_the_setting():
    """Documented because it is silent.

    Someone debugging a TLS problem will reach for `?sslmode=disable` on the
    URL first, and it does nothing -- `DB_SSL_REQUIRE` is what decides.
    """
    ignored = _database(
        {'DATABASE_URL': 'postgres://u:p@db.example.com:5432/mydb?sslmode=disable'}
    )
    honoured = _database(
        {
            'DATABASE_URL': 'postgres://u:p@db.example.com:5432/mydb',
            'DB_SSL_REQUIRE': 'false',
        }
    )

    assert ignored['sslmode'] == 'require'
    assert honoured['sslmode'] is None


def test_the_url_wins_over_the_individual_variables():
    resolved = _database(
        {
            'DATABASE_URL': 'postgres://u:p@fromurl.example.com:5432/urldb',
            'DB_HOST': 'ignored.example.com',
            'DB_NAME': 'ignored',
        }
    )

    assert resolved['host'] == 'fromurl.example.com'
    assert resolved['name'] == 'urldb'


def test_a_half_configured_remote_host_is_refused_rather_than_dialled():
    """DB_HOST set by hand on a managed host, with the rest left at defaults.

    Without the guard the process boots, blocks in the entrypoint's connection
    loop, and the platform reports a missing port rather than the missing
    password.
    """
    started, error = _boot(
        {
            'DJANGO_ENVIRONMENT': 'production',
            'SECRET_KEY': REQUIRED_IN_PRODUCTION['SECRET_KEY'],
            'ALLOWED_HOSTS': REQUIRED_IN_PRODUCTION['ALLOWED_HOSTS'],
            'FRONTEND_URL': REQUIRED_IN_PRODUCTION['FRONTEND_URL'],
            'DB_HOST': 'db.example.com',
        }
    )

    assert not started
    assert 'DB_PASSWORD' in error, error
