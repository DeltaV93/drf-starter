"""
Settings shared by every environment.

Environment-specific modules (development.py, production.py, testing.py)
import everything from here and override what differs. Never import this
module directly as DJANGO_SETTINGS_MODULE -- use `template.settings`, which
picks the right environment based on DJANGO_ENVIRONMENT.

Every value that differs between deployments is read from the environment.
See .env.example for the full list.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=BASE_DIR / '.env')

ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'development')


# --------------------------------------------------------------------------
# Environment helpers
# --------------------------------------------------------------------------


def env_bool(name, default=False):
    """Read a boolean from the environment. Accepts 1/true/yes/on."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    """Read a comma-separated list from the environment."""
    value = os.environ.get(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def env_int(name, default):
    """Read an integer from the environment, falling back on a bad value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be an integer, got {value!r}') from exc


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if ENVIRONMENT in {'development', 'testing'}:
        # Convenience only: a fresh key every restart invalidates sessions and
        # password reset links. Set SECRET_KEY in .env to keep them stable.
        # testing.py overrides this with a fixed key.
        SECRET_KEY = f'django-insecure-{get_random_secret_key()}'
    else:
        raise ImproperlyConfigured(
            f'SECRET_KEY must be set when DJANGO_ENVIRONMENT is "{ENVIRONMENT}". '
            'Generate one with: python -c '
            '"from django.core.management.utils import get_random_secret_key as k; print(k())"'
        )

# Overridden per environment; this default is the safe one.
DEBUG = False

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')

# Feature flags. Both subsystems are optional -- see README for how to remove
# them entirely rather than just switching them off.
STRIPE_ENABLED = env_bool('STRIPE_ENABLED', default=False)
SOCIAL_AUTH_ENABLED = env_bool('SOCIAL_AUTH_ENABLED', default=False)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'django_ses',
    # Local apps
    'apps.core',
    'apps.users',
    'apps.authentication',
]

if STRIPE_ENABLED:
    INSTALLED_APPS.append('apps.subscriptions')

if SOCIAL_AUTH_ENABLED:
    INSTALLED_APPS.append('social_django')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if STRIPE_ENABLED:
    MIDDLEWARE.append('apps.subscriptions.middleware.SubscriptionMiddleware')

ROOT_URLCONF = 'template.urls'

_CONTEXT_PROCESSORS = [
    'django.template.context_processors.debug',
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
]

if SOCIAL_AUTH_ENABLED:
    _CONTEXT_PROCESSORS += [
        'social_django.context_processors.backends',
        'social_django.context_processors.login_redirect',
    ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': _CONTEXT_PROCESSORS,
        },
    },
]

WSGI_APPLICATION = 'template.wsgi.application'
ASGI_APPLICATION = 'template.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'app'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': env_int('DB_CONN_MAX_AGE', 60),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']


# --------------------------------------------------------------------------
# Static and media files
# --------------------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}


# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('THROTTLE_ANON', '100/day'),
        'user': os.environ.get('THROTTLE_USER', '1000/day'),
        # Applied to unauthenticated auth endpoints, which are the ones worth
        # rate limiting far more aggressively than general anonymous traffic.
        'login': os.environ.get('THROTTLE_LOGIN', '10/min'),
        'password_reset': os.environ.get('THROTTLE_PASSWORD_RESET', '5/hour'),
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': os.environ.get('API_TITLE', 'DRF Starter API'),
    'DESCRIPTION': os.environ.get('API_DESCRIPTION', 'API for DRF Starter'),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


# --------------------------------------------------------------------------
# Sessions, CSRF and CORS
#
# The frontend authenticates with session cookies, so CSRF protection is on
# and the browser-facing cookie/origin settings below have to agree with
# wherever the SPA is actually served from.
# --------------------------------------------------------------------------

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', default=[FRONTEND_URL])
CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', default=[FRONTEND_URL])

SESSION_COOKIE_HTTPONLY = True
# Left readable by JavaScript on purpose: the SPA reads the csrftoken cookie
# and echoes it back in the X-CSRFToken header. This is Django's own default.
CSRF_COOKIE_HTTPONLY = False

# Overridden per environment. SameSite=None requires Secure=True in every
# current browser, so these two always move together.
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.environ.get('CSRF_COOKIE_SAMESITE', 'Lax')
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=True)


# --------------------------------------------------------------------------
# Celery
# --------------------------------------------------------------------------

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f'{REDIS_URL}/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f'{REDIS_URL}/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}


# --------------------------------------------------------------------------
# Email
#
# Configured in base so that every environment has a working backend.
# development.py swaps in the console backend.
# --------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django_ses.SESBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = os.environ.get('AWS_SES_REGION_NAME', 'us-east-1')
AWS_SES_REGION_ENDPOINT = f'email.{AWS_SES_REGION_NAME}.amazonaws.com'

# How long password reset and email verification links stay valid.
PASSWORD_RESET_TIMEOUT = env_int('PASSWORD_RESET_TIMEOUT', 60 * 60 * 24 * 3)


# --------------------------------------------------------------------------
# Authentication backends
# --------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

if SOCIAL_AUTH_ENABLED:
    AUTHENTICATION_BACKENDS = [
        'social_core.backends.google.GoogleOAuth2',
        'social_core.backends.linkedin.LinkedinOAuth2',
        *AUTHENTICATION_BACKENDS,
    ]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_SECRET')
SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = os.environ.get('LINKEDIN_OAUTH2_KEY')
SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = os.environ.get('LINKEDIN_OAUTH2_SECRET')


# --------------------------------------------------------------------------
# Stripe
# --------------------------------------------------------------------------

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_SUCCESS_URL = os.environ.get(
    'STRIPE_SUCCESS_URL', f'{FRONTEND_URL}/subscription/success'
)
STRIPE_CANCEL_URL = os.environ.get('STRIPE_CANCEL_URL', f'{FRONTEND_URL}/subscription/cancel')
# Days a past-due subscription keeps working before access is cut off.
SUBSCRIPTION_GRACE_PERIOD_DAYS = env_int('SUBSCRIPTION_GRACE_PERIOD_DAYS', 14)


# --------------------------------------------------------------------------
# Logging
#
# Container-native: everything goes to stdout/stderr and the platform is
# responsible for collection. Do not add FileHandlers here.
# --------------------------------------------------------------------------

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', LOG_LEVEL),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
