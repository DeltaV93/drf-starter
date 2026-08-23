"""Local development settings."""

import os

from .base import *
from .base import FRONTEND_URL, INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, env_bool, env_list

DEBUG = True

ALLOWED_HOSTS = env_list(
    'ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', '0.0.0.0', 'host.docker.internal', 'web'],
)

# Emails print to the console instead of hitting SES. Set EMAIL_BACKEND in
# .env to django_ses.SESBackend if you want to test real delivery.
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

# Cookies cannot be Secure over plain http, and SameSite=None requires Secure,
# so local development uses Lax + insecure. The SPA and API are same-site via
# localhost, which Lax handles fine.
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=False)
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.environ.get('CSRF_COOKIE_SAMESITE', 'Lax')

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        FRONTEND_URL,
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'https://localhost:3000',
        'https://127.0.0.1:3000',
    ],
)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', default=CORS_ALLOWED_ORIGINS)

# The browsable API is genuinely useful locally and off everywhere else.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# Django Debug Toolbar, only when it is actually installed. Keeping it optional
# means `pip install -r requirements/base.txt` still boots in development.
if env_bool('ENABLE_DEBUG_TOOLBAR', default=True):
    try:
        import debug_toolbar  # noqa: F401
    except ImportError:
        pass
    else:
        INSTALLED_APPS = [*INSTALLED_APPS, 'debug_toolbar']
        MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
        DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG}
