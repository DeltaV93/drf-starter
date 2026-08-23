"""Production settings.

Everything here is driven by the environment. Run
`python manage.py check --deploy` against this module before shipping.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import MIDDLEWARE, STORAGES, env_bool, env_int, env_list

DEBUG = False

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must be set in production, e.g. '
        'ALLOWED_HOSTS=example.com,www.example.com'
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
