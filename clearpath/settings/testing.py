"""Settings for the test suite.

Defaults to SQLite and in-memory backends so `pytest` runs with no services
running. CI points DB_ENGINE at Postgres so the suite also exercises the real
database -- see .github/workflows/ci.yml.
"""

import os

# The billing app is opt-in, and base.py reads STRIPE_ENABLED while it is
# imported -- so this has to be set before that import, not after. The suite
# exercises billing by default; CI additionally runs with STRIPE_ENABLED=false
# to prove the project still boots and passes without it.
os.environ.setdefault('STRIPE_ENABLED', 'true')
os.environ.setdefault('ORGANIZATIONS_ENABLED', 'true')
os.environ.setdefault('API_KEYS_ENABLED', 'true')
os.environ.setdefault('AUDIT_LOG_ENABLED', 'true')
os.environ.setdefault('TWO_FACTOR_ENABLED', 'true')
os.environ.setdefault('UPLOADS_ENABLED', 'true')
os.environ.setdefault('MCP_SERVER_ENABLED', 'true')
os.environ.setdefault('MCP_OAUTH_ENABLED', 'true')
# The issuer and audience have no defaults -- base.py refuses to boot without
# them when the flag is on, because comparing a token claim against an empty
# string would accept somebody else's token. These are the values the forgery
# tests mint against; nothing here reaches the network for them.
os.environ.setdefault('MCP_OAUTH_ISSUER', 'https://auth.example.test/')
os.environ.setdefault('MCP_OAUTH_AUDIENCE', 'https://app.example.test/mcp')
os.environ.setdefault('MCP_CLIENT_ENABLED', 'true')
# The client refuses to call without a model, on purpose -- see the setting's
# comment. The tests never reach a real API, so this only has to be non-empty
# and recognisable in a failure message.
os.environ.setdefault('MCP_CLIENT_MODEL', 'model-under-test')

# Pointing DJANGO_SETTINGS_MODULE straight at this module -- which is how the
# suite runs -- leaves DJANGO_ENVIRONMENT unset, so base.py would call the
# environment 'development'. Anything keyed off it would then be wrong during
# a test run, including the guard that keeps Sentry from reporting deliberate
# test failures into a real project.
os.environ.setdefault('DJANGO_ENVIRONMENT', 'testing')

from .base import *
from .base import BASE_DIR

DEBUG = False

ALLOWED_HOSTS = ['*']

SECRET_KEY = 'django-insecure-test-key-not-used-outside-the-test-suite'

if os.environ.get('DB_ENGINE') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'test_app'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
            'TEST': {'NAME': ':memory:'},
        }
    }

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Pinned off so the suite behaves the same whether or not someone has run
# a frontend build -- SERVE_SPA otherwise defaults to whether website/dist
# exists, which would make the URLconf depend on the working tree.
# The catch-all itself is covered by apps/core/tests/test_spa.py, which
# builds its own URLconf.
SERVE_SPA = False

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Fast hashing keeps the suite quick; never use this outside tests.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Throttling would make the suite order-dependent. The scopes have to stay
# defined -- views name them explicitly in throttle_classes -- so the limits
# are raised out of reach instead of removed. Rate limiting itself is covered
# by apps/authentication/tests/test_throttling.py, which sets its own rates.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100000/day',
        'user': '100000/day',
        'login': '100000/day',
        'password_reset': '100000/day',
        'api_key': '100000/day',
        'data_export': '100000/day',
    },
}

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
