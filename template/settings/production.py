"""Production settings.

Everything here is driven by the environment. Run
`python manage.py check --deploy` against this module before shipping.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import (
    CSRF_TRUSTED_ORIGINS,
    MIDDLEWARE,
    SERVE_SPA,
    SPA_DIST_DIR,
    STORAGES,
    env_bool,
    env_int,
    env_list,
)

DEBUG = False

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')

# Platforms that assign a domain (Railway, Render, Fly) only expose it after
# the first deploy, so requiring ALLOWED_HOSTS up front would make that first
# boot crash. Pick the injected domain up automatically when it is there.
_PLATFORM_DOMAIN = (
    os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    or os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    or (os.environ.get('FLY_APP_NAME') and f'{os.environ["FLY_APP_NAME"]}.fly.dev')
)
if _PLATFORM_DOMAIN and _PLATFORM_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _PLATFORM_DOMAIN]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must be set in production, e.g. '
        'ALLOWED_HOSTS=example.com,www.example.com'
    )

# base.py falls back to DB_HOST=localhost, which is right for local
# development and essentially never right in production -- there is no
# Postgres inside the application container. Without this guard an unset
# DATABASE_URL surfaces as a connection-refused loop against 127.0.0.1
# rather than as the configuration mistake it is.
if not os.environ.get('DATABASE_URL') and not os.environ.get('DB_HOST'):
    raise ImproperlyConfigured(
        'No database is configured. Set DATABASE_URL -- managed hosts expose '
        'one, and on Railway you reference it as ${{Postgres.DATABASE_URL}} in '
        "the web service's variables (adding the Postgres plugin alone does not "
        'inject it). Alternatively set DB_HOST, DB_NAME, DB_USER and '
        'DB_PASSWORD individually. Refusing to fall back to localhost.'
    )

# Session auth needs the origin trusted for CSRF as well as the host allowed.
if _PLATFORM_DOMAIN:
    _PLATFORM_ORIGIN = f'https://{_PLATFORM_DOMAIN}'
    if _PLATFORM_ORIGIN not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, _PLATFORM_ORIGIN]
    # Same-origin SPA: the frontend is this domain, so it is also the base for
    # the links in password reset and verification emails.
    if not os.environ.get('FRONTEND_URL'):
        FRONTEND_URL = _PLATFORM_ORIGIN
        STRIPE_SUCCESS_URL = os.environ.get(
            'STRIPE_SUCCESS_URL', f'{FRONTEND_URL}/subscription/success'
        )
        STRIPE_CANCEL_URL = os.environ.get(
            'STRIPE_CANCEL_URL', f'{FRONTEND_URL}/subscription/cancel'
        )

# --------------------------------------------------------------------------
# HTTPS and security headers
# --------------------------------------------------------------------------

# Terminating TLS at a load balancer means Django only learns the original
# scheme from this header. Leave SECURE_PROXY_SSL_HEADER unset if the app
# itself terminates TLS.
if env_bool('USE_X_FORWARDED_PROTO', default=True):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --------------------------------------------------------------------------
# Static files
#
# WhiteNoise serves compressed, hashed static files straight from the app, so
# no separate static host is required. Swap STORAGES['staticfiles'] for an S3
# backend if you would rather serve from a CDN.
# --------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    *[m for m in MIDDLEWARE if m != 'django.middleware.security.SecurityMiddleware'],
]

STORAGES = {
    **STORAGES,
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# WhiteNoise also serves the SPA build at the root. Vite already hashes its
# asset filenames, so running that output through ManifestStaticFilesStorage
# would fight it -- WHITENOISE_ROOT serves the directory as-is instead.
if SERVE_SPA:
    WHITENOISE_ROOT = SPA_DIST_DIR
    WHITENOISE_INDEX_FILE = True
