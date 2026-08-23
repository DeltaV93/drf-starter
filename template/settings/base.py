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
from urllib.parse import urlparse

import dj_database_url
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


def env_float(name, default):
    """Read a float from the environment, refusing a bad value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be a number, got {value!r}') from exc


def is_local_db_host(host):
    """True when a database host is this machine or the compose service."""
    return (host or '').lower() in {'localhost', '127.0.0.1', '::1', 'db', ''}


def _is_local_url(url):
    """True when a database URL points at this machine or a compose service."""
    return is_local_db_host(urlparse(url).hostname)


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
# Teams. Off by default because the single-user shape is the simpler one
# and costs nothing; turn it on for B2B. Nothing outside apps/organizations
# holds a foreign key into it, so it comes out cleanly.
ORGANIZATIONS_ENABLED = env_bool('ORGANIZATIONS_ENABLED', default=False)
# Programmatic access. Session cookies serve a browser and nothing else --
# no CLI, no CI job, no server-to-server integration.
API_KEYS_ENABLED = env_bool('API_KEYS_ENABLED', default=False)
# An append-only record of security-relevant actions. Off by default; the
# first thing a B2B security review asks for.
AUDIT_LOG_ENABLED = env_bool('AUDIT_LOG_ENABLED', default=False)
# TOTP second factor. Gates behaviour and URLs rather than INSTALLED_APPS:
# the models live in apps.authentication, which is always installed, so the
# migration does not appear and disappear with the flag.
TWO_FACTOR_ENABLED = env_bool('TWO_FACTOR_ENABLED', default=False)
# File uploads. Off by default: the local filesystem is ephemeral on every
# managed host, so this is not useful until S3 is configured.
UPLOADS_ENABLED = env_bool('UPLOADS_ENABLED', default=False)

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

if ORGANIZATIONS_ENABLED:
    INSTALLED_APPS.append('apps.organizations')

if API_KEYS_ENABLED:
    INSTALLED_APPS.append('apps.api_keys')

if AUDIT_LOG_ENABLED:
    INSTALLED_APPS.append('apps.audit')

if UPLOADS_ENABLED:
    INSTALLED_APPS.append('apps.uploads')

MIDDLEWARE = [
    # First on purpose: health probes must be answered before the SSL
    # redirect and before ALLOWED_HOSTS validation, because platforms probe
    # over plain HTTP with their own Host header. See apps/core/middleware.py.
    'apps.core.middleware.HealthCheckMiddleware',
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

# --------------------------------------------------------------------------
# Single-page app
#
# In the container the built SPA sits in website/dist and Django serves it,
# which keeps it same-origin with the API -- what the session-cookie and CSRF
# design assumes. Locally the directory does not exist and `make fe-dev`
# serves the SPA from Vite instead, so this switches itself off.
# --------------------------------------------------------------------------

SPA_DIST_DIR = BASE_DIR / 'website' / 'dist'
SERVE_SPA = env_bool('SERVE_SPA', default=(SPA_DIST_DIR / 'index.html').exists())

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
        'DIRS': [BASE_DIR / 'templates', *([SPA_DIST_DIR] if SERVE_SPA else [])],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': _CONTEXT_PROCESSORS,
        },
    },
]

WSGI_APPLICATION = 'template.wsgi.application'
ASGI_APPLICATION = 'template.asgi.application'

# Managed hosts (Railway, Render, Heroku, Fly) hand you a single DATABASE_URL
# rather than separate parts, so it wins when present. The individual DB_*
# variables remain the path for local development and docker compose.
DB_CONN_MAX_AGE = env_int('DB_CONN_MAX_AGE', 60)
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=DB_CONN_MAX_AGE,
            # Managed Postgres is reached over the network and expects TLS;
            # a URL pointing at localhost is assumed to be a local instance.
            ssl_require=env_bool('DB_SSL_REQUIRE', default=not _is_local_url(DATABASE_URL)),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'app'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': DB_CONN_MAX_AGE,
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
# Uploads
#
# The default filesystem backend is a DEVELOPMENT CONVENIENCE ONLY. Container
# filesystems are ephemeral: on Railway, Render, Fly or any rebuild, every
# uploaded file is gone, silently, leaving rows pointing at nothing. Setting
# AWS_STORAGE_BUCKET_NAME swaps in S3, which is what a deployment needs.
# --------------------------------------------------------------------------

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')

if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        **STORAGES,
        'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
    }
    # Read from the environment rather than reusing AWS_SES_REGION_NAME:
    # that is defined further down, in the email section, so referring to it
    # here is a NameError -- and one that only fires for deployments that
    # actually set a bucket.
    AWS_S3_REGION_NAME = (
        os.environ.get('AWS_S3_REGION_NAME')
        or os.environ.get('AWS_SES_REGION_NAME')
        or 'us-east-1'
    )
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL') or None
    # Private by default. A public bucket turns every unguessable key into a
    # permanent public URL the moment one leaks.
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False

# Sniffed from the file's own bytes, never from the Content-Type header or the
# extension. Keep this list short: whatever is here is what the application
# will accept and later serve.
UPLOAD_ALLOWED_TYPES = env_list(
    'UPLOAD_ALLOWED_TYPES',
    default=['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'],
)
UPLOAD_MAX_BYTES = env_int('UPLOAD_MAX_BYTES', 5 * 1024 * 1024)
UPLOAD_URL_EXPIRY_SECONDS = env_int('UPLOAD_URL_EXPIRY_SECONDS', 300)


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
        # Machine traffic gets its own budget: an integration is
        # legitimately noisier than a person, and a runaway script must not
        # exhaust the interactive user's allowance.
        'api_key': os.environ.get('THROTTLE_API_KEY', '10000/day'),
        # Building an export walks every table the user touches, and sends
        # mail to an address. Unthrottled it is both a load amplifier and a
        # way to make the application send someone repeated email.
        'data_export': os.environ.get('THROTTLE_DATA_EXPORT', '3/day'),
    },
}

if API_KEYS_ENABLED:
    # Appended, not substituted: the browser keeps using session cookies.
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
        *REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'],
        'apps.api_keys.authentication.APIKeyAuthentication',
    ]
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
        *REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'],
        'apps.api_keys.throttles.APIKeyRateThrottle',
    ]

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

# Hand rendered messages to Celery instead of sending them in the request.
# Off by default because it needs a worker running; the default `make up` has
# no worker, and a queued message nobody drains is worse than a slow one.
# Templates are still rendered inline either way -- only delivery moves -- so
# a broken template fails the request rather than a task nobody is watching.
EMAIL_ASYNC = env_bool('EMAIL_ASYNC', default=False)

# How long audit entries are kept. prune_audit_log drops older ones; nothing
# expires on its own, so schedule that command if the table matters.
AUDIT_LOG_RETENTION_DAYS = env_int('AUDIT_LOG_RETENTION_DAYS', 365)

# How long a half-finished login stays verifiable. Longer than this and a
# password-verified state sits in a session cookie indefinitely.
TWO_FACTOR_PENDING_TIMEOUT = env_int('TWO_FACTOR_PENDING_TIMEOUT', 300)

# Encrypts TOTP secrets at rest. Falls back to SECRET_KEY -- see the
# rotation warning in apps/authentication/two_factor.py before relying on
# that fallback.
TWO_FACTOR_SECRET_KEY = os.environ.get('TWO_FACTOR_SECRET_KEY', '')

# How long a data-export download link stays usable. Signed and
# time-limited rather than a stored row: nothing to clean up, and an aged
# link stops working without anyone expiring it.
GDPR_EXPORT_LINK_TIMEOUT = env_int('GDPR_EXPORT_LINK_TIMEOUT', 24 * 3600)

# How long an organization invitation stays redeemable.
INVITATION_EXPIRY_DAYS = env_int('INVITATION_EXPIRY_DAYS', 7)

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

# Which providers the frontend should offer. Derived from the keys that are
# actually configured, so a button never appears for a provider that would
# fail on the redirect.
SOCIAL_AUTH_PROVIDERS = []
if SOCIAL_AUTH_ENABLED:
    if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
        SOCIAL_AUTH_PROVIDERS.append('google-oauth2')
    if SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY:
        SOCIAL_AUTH_PROVIDERS.append('linkedin-oauth2')

if SOCIAL_AUTH_ENABLED:
    # Spelled out as dotted paths rather than imported from the app module.
    # Importing app code from settings reaches the model registry before it is
    # ready, and an import that looks unused to a linter gets removed -- which
    # silently left this setting undefined once already.
    #
    # This is social_core's default pipeline with ONE step removed:
    # social_auth.associate_by_email, which hands a social identity any
    # existing account carrying the same address. That is an account-takeover
    # path; see apps/authentication/social_pipeline.py.
    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.auth_allowed',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.user.get_username',
        # Before create_user: afterwards the account would already exist.
        'apps.authentication.social_pipeline.refuse_silent_takeover',
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
        'apps.authentication.social_pipeline.mark_email_verified',
    )

    # Where social_django sends the browser once the provider comes back. Both
    # are SPA routes; the login page reads the error from the query string.
    SOCIAL_AUTH_LOGIN_REDIRECT_URL = f'{FRONTEND_URL}/profile'
    SOCIAL_AUTH_LOGIN_ERROR_URL = f'{FRONTEND_URL}/login'
    # Turn a pipeline exception into a redirect with a message rather than a
    # 500 page the user cannot act on.
    SOCIAL_AUTH_RAISE_EXCEPTIONS = False

    # Only the fields the pipeline needs. Providers return far more, and
    # storing it is a data-protection liability nobody asked for.
    SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', 'username']
    SOCIAL_AUTH_USER_FIELDS = ['username', 'email', 'first_name', 'last_name']

    # The state parameter is what stops an attacker completing the flow in
    # someone else's browser; social_core defaults it on, pinned here so a
    # future edit has to be deliberate.
    SOCIAL_AUTH_GOOGLE_OAUTH2_USE_STATE = True
    SOCIAL_AUTH_LINKEDIN_OAUTH2_USE_STATE = True

    SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']


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


# --------------------------------------------------------------------------
# Error tracking
#
# Presence-gated rather than flag-gated: setting SENTRY_DSN is the only thing
# that turns it on, and nothing is imported without it. Without this a
# production 500 exists only in a log line nobody is reading.
# --------------------------------------------------------------------------

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

# Never during a test run. A CI machine with a DSN in its environment would
# otherwise fill a real project with noise from deliberately-failing tests.
if SENTRY_DSN and ENVIRONMENT != 'testing':
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        # Whatever the platform exposes; a release makes a traceback point at
        # a commit instead of at "production".
        release=(
            os.environ.get('SENTRY_RELEASE')
            or os.environ.get('RAILWAY_GIT_COMMIT_SHA')
            or os.environ.get('RENDER_GIT_COMMIT')
            or None
        ),
        # Off on purpose. Turning it on ships email addresses, usernames and
        # IP addresses to a third party, which is a decision to make
        # deliberately and document, not to inherit from a default.
        send_default_pii=env_bool('SENTRY_SEND_PII', default=False),
        traces_sample_rate=env_float('SENTRY_TRACES_SAMPLE_RATE', 0.0),
    )
