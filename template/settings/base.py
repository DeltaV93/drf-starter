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
from datetime import timedelta
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
# The MCP endpoint. Off by default: it makes the application callable by
# agents, which is a decision to take deliberately rather than inherit.
# Gates the ASGI route rather than any URL -- the endpoint is mounted beside
# Django, not inside its URLconf.
MCP_SERVER_ENABLED = env_bool('MCP_SERVER_ENABLED', default=False)
# OAuth 2.1 bearer tokens, validated against an external authorization server.
# A separate flag from MCP_SERVER_ENABLED on purpose: the two are independent.
# The MCP endpoint forwards whatever Authorization header it is given, so it
# works on API keys alone; and bearer tokens are useful to the REST API whether
# or not anything MCP is switched on. Turning this on requires an authorization
# server to point at, which is why it cannot default to true.
MCP_OAUTH_ENABLED = env_bool('MCP_OAUTH_ENABLED', default=False)
# Calling *out* to other people's MCP servers, for agentic features. The
# mirror of MCP_SERVER_ENABLED and entirely independent of it: an application
# can be agent-callable without itself being an agent, and the other way
# round.
MCP_CLIENT_ENABLED = env_bool('MCP_CLIENT_ENABLED', default=False)
# Push notification device registry, for the mobile client. Off by default:
# it is useless without credentials for a push service, and an app that never
# sends a notification should not be storing device tokens.
PUSH_ENABLED = env_bool('PUSH_ENABLED', default=False)

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
    # Installed unconditionally, and that is deliberate. It is what makes
    # `auth/token/revoke/` mean anything: without a blacklist a refresh token
    # stays valid for its full lifetime after the user taps "log out", and a
    # stolen one cannot be taken away. Rotation writes a row per refresh, so
    # `flushexpiredtokens` belongs on a schedule -- see the README.
    'rest_framework_simplejwt.token_blacklist',
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

if MCP_SERVER_ENABLED:
    INSTALLED_APPS.append('apps.mcp_server')

if MCP_OAUTH_ENABLED:
    INSTALLED_APPS.append('apps.mcp_oauth')

if MCP_CLIENT_ENABLED:
    INSTALLED_APPS.append('apps.mcp_client')

if PUSH_ENABLED:
    INSTALLED_APPS.append('apps.push')

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
        # Bearer tokens for the mobile app, FIRST and unconditionally.
        #
        # First because the class below it that also reads `Authorization:
        # Bearer` -- apps.mcp_oauth -- *raises* on a token it cannot validate
        # rather than declining it, so anything ordered after that one never
        # runs. This class declines instead: a token whose `iss` is not ours
        # returns None and the chain continues, which is what lets the two
        # bearer schemes share one header. See its docstring for how it keeps
        # the RFC 9728 challenge that position used to be responsible for.
        'apps.authentication.authentication_token.MobileJWTAuthentication',
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

if MCP_OAUTH_ENABLED:
    # Added to the list, not substituted for it: the browser keeps using
    # session cookies and any API keys keep working. Being in the default list
    # is also what gives the MCP endpoint bearer-token auth for free, because
    # apps/mcp_server forwards the caller's Authorization header into this
    # same stack -- there is no second auth path to keep in step.
    #
    # Ahead of SessionAuthentication, and that relative position is
    # load-bearing. DRF builds the WWW-Authenticate header from
    # `authenticators[0]` alone. SessionAuthentication offers none, so with it
    # first DRF has nothing to challenge with and answers 403 instead of 401 --
    # and the RFC 9728 `resource_metadata` hint never reaches the client. That
    # hint is how an MCP client discovers the authorization server, so losing
    # it means nothing can connect unaided.
    #
    # It is no longer index 0, because MobileJWTAuthentication has to see a
    # bearer token first (that class declines what is not its own; this one
    # raises). The challenge is preserved anyway: MobileJWTAuthentication
    # delegates `authenticate_header` here whenever this flag is on, which
    # apps/mcp_oauth/tests pin. Ordering costs nothing else -- both classes
    # return None for any request that is not `Authorization: Bearer ...`.
    _session_auth = 'rest_framework.authentication.SessionAuthentication'
    _mcp_auth = 'apps.mcp_oauth.authentication.BearerTokenAuthentication'
    _classes = list(REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
    _classes.insert(_classes.index(_session_auth), _mcp_auth)
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = _classes

# --------------------------------------------------------------------------
# Bearer tokens for the mobile client
#
# The browser authenticates with a session cookie and a CSRF token, which is
# the right answer for a same-origin SPA and the wrong one for a phone: a
# native client has no cookie jar worth relying on, and CSRF is meaningless
# without one. So the mobile app carries a short-lived access token and
# refreshes it against a long-lived one held in the platform keystore.
#
# This is added to the authentication classes, never substituted for them --
# the website's session auth is untouched, and apps/authentication/tests/
# test_csrf.py still pins that contract.
# --------------------------------------------------------------------------

# What the `iss` claim carries, and the only thing that tells our tokens apart
# from another bearer scheme's on the same header. MobileJWTAuthentication
# routes on it; SimpleJWT verifies it. Changing it invalidates every token in
# circulation, which is a blunt but effective revocation of last resort.
TOKEN_ISSUER = os.environ.get('TOKEN_ISSUER', 'drf-starter')

SIMPLE_JWT = {
    # Short, because an access token cannot be revoked before it expires --
    # nothing checks a database on the way through. The refresh token is the
    # one with a revocation story, which is why it is the only one stored.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env_int('ACCESS_TOKEN_MINUTES', 15)),
    # Long, because the alternative is asking someone to type a password into
    # a phone every fortnight. Rotation is what makes that safe.
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env_int('REFRESH_TOKEN_DAYS', 30)),
    # Every refresh issues a new pair and blacklists the one just spent. A
    # stolen refresh token is then good for exactly one use, and the moment
    # either party spends it the other's next attempt fails -- which is the
    # only signal a server gets that a token leaked.
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'ISSUER': TOKEN_ISSUER,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# How long the client has to answer the second-factor prompt before the
# challenge issued by auth/token/ stops being redeemable.
TOKEN_TWO_FACTOR_CHALLENGE_SECONDS = env_int('TOKEN_TWO_FACTOR_CHALLENGE_SECONDS', 300)


# --------------------------------------------------------------------------
# Mobile app identity, for deep links
#
# The backend emails links like {FRONTEND_URL}/verify-email/<uid>/<token>.
# Publishing the two association documents below is what makes the operating
# system hand those same URLs to the installed app instead of the browser --
# so one email works for both clients and there is no second link to keep in
# step. Each document is served only when its half is configured; unset, the
# path 404s, which is the correct answer for a deployment with no app.
#
# See apps/core/views.py (AppleAppSiteAssociationView, AssetLinksView).
# --------------------------------------------------------------------------

# "<TeamID>.<bundle identifier>", e.g. ABCDE12345.com.example.app
MOBILE_IOS_APP_ID = os.environ.get('MOBILE_IOS_APP_ID', '')

# The Android application id, e.g. com.example.app
MOBILE_ANDROID_PACKAGE = os.environ.get('MOBILE_ANDROID_PACKAGE', '')

# SHA-256 fingerprints of the signing certificates, colon-separated hex.
# More than one is normal: Play App Signing and the upload key differ.
MOBILE_ANDROID_SHA256_FINGERPRINTS = env_list('MOBILE_ANDROID_SHA256_FINGERPRINTS')

# The custom scheme the app also answers on, used in development where there
# is no verified domain. Mirrors `scheme` in mobile/app.json.
MOBILE_APP_SCHEME = os.environ.get('MOBILE_APP_SCHEME', 'drfstarter')

# Which client-side paths the app claims. Anything not listed keeps opening
# in the browser, which is what you want for marketing pages and the admin.
MOBILE_DEEP_LINK_PATHS = env_list(
    'MOBILE_DEEP_LINK_PATHS',
    default=['/verify-email/*', '/confirm-password/*', '/invitations/*'],
)

SPECTACULAR_SETTINGS = {
    'TITLE': os.environ.get('API_TITLE', 'DRF Starter API'),
    'DESCRIPTION': os.environ.get('API_DESCRIPTION', 'API for DRF Starter'),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'ENUM_NAME_OVERRIDES': {},
}

# Two different fields are called `role` -- the product-wide one on the user
# and the per-organization one on a membership -- and they are deliberately
# separate. Left alone the generator resolves the clash with a hashed name
# like `Role6d0Enum`, which reads as a bug in the schema. Naming them is also
# the only way `python manage.py spectacular --fail-on-warn` passes, which CI
# requires. Keyed by dotted path, so it is only added when the app is
# installed and the flag stays independent.
SPECTACULAR_SETTINGS['ENUM_NAME_OVERRIDES']['UserRoleEnum'] = (
    'apps.users.models.CustomUser.Role'
)
if ORGANIZATIONS_ENABLED:
    SPECTACULAR_SETTINGS['ENUM_NAME_OVERRIDES']['MembershipRoleEnum'] = (
        'apps.organizations.models.Membership.Role'
    )


# --------------------------------------------------------------------------
# MCP
#
# The endpoint is mounted by template/asgi.py at MCP_MOUNT_PATH, beside Django
# rather than inside its URLconf, because the SDK's transport is ASGI-only.
# --------------------------------------------------------------------------

# What a client shows in its list of connected servers. Defaults to the same
# value API_TITLE uses -- read from the environment rather than from that
# name, which is only ever a literal inside SPECTACULAR_SETTINGS.
MCP_SERVER_NAME = os.environ.get(
    'MCP_SERVER_NAME', os.environ.get('API_TITLE', 'DRF Starter API')
)

# Where the endpoint is mounted. Changing it means changing what every
# connected client has configured, so it is a setting rather than a constant.
MCP_MOUNT_PATH = os.environ.get('MCP_MOUNT_PATH', '/mcp')


# --------------------------------------------------------------------------
# MCP client -- calling out to other servers
#
# Which servers exist is decided by the modules under
# apps/mcp_client/servers/, in the repository and reviewable in a diff. These
# settings choose which of those are live and how the call is made; they
# cannot introduce a server nobody wrote a file for.
# --------------------------------------------------------------------------

# Slugs to enable. Empty means every server defined under servers/ -- which is
# already a set bounded by what is in the repository, so this is a way to run
# a subset per environment rather than a security boundary. A slug with no
# module raises at startup rather than being silently ignored.
MCP_CLIENT_SERVERS = env_list('MCP_CLIENT_SERVERS')

# The model outbound calls use. No default on purpose: a model ID baked into a
# template ages quietly -- it keeps working while better models ship and
# nothing ever fails to make anyone notice. Set it to a current ID; the client
# raises a clear error rather than guessing.
MCP_CLIENT_MODEL = os.environ.get('MCP_CLIENT_MODEL', '')

# Where Claude is being called. The MCP connector is available on the Claude
# API and Claude Platform on AWS only -- not Bedrock, not Vertex, which route
# to Claude but not through the endpoint that fetches an MCP server. A server
# whose definition says transport='local' works on any of them.
MCP_CLIENT_PROVIDER = os.environ.get('MCP_CLIENT_PROVIDER', 'anthropic')

MCP_CLIENT_MAX_TOKENS = env_int('MCP_CLIENT_MAX_TOKENS', default=4096)

# How many times the local transport will hand a tool result back to the model
# before giving up. Only the local transport runs the loop -- with the
# connector, Anthropic does. A model that keeps asking for tools would
# otherwise loop until the process is killed.
MCP_CLIENT_MAX_TOOL_ROUNDS = env_int('MCP_CLIENT_MAX_TOOL_ROUNDS', default=8)
MCP_CLIENT_TIMEOUT_SECONDS = env_float('MCP_CLIENT_TIMEOUT_SECONDS', default=60.0)

# Encrypts a stored per-user credential at rest. Falls back to SECRET_KEY --
# rotating that makes every stored credential undecryptable and every
# connection has to be re-authorised. Recoverable, but a surprise.
MCP_CLIENT_SECRET_KEY = os.environ.get('MCP_CLIENT_SECRET_KEY', '')

# --------------------------------------------------------------------------
# OAuth 2.1 -- resource server only
#
# This application validates access tokens. It never issues them. RFC 9728
# formalises that split and MCP's auth spec adopts it: everything genuinely
# dangerous -- authorize, consent, code exchange, PKCE, redirect-URI matching,
# token signing, key rotation -- belongs to the authorization server, which is
# not this. See apps/mcp_oauth/validation.py.
#
# There is no OAuth server library in requirements: PyJWT and cryptography are
# already installed and verification is all this side needs.
# --------------------------------------------------------------------------

if MCP_OAUTH_ENABLED:
    # The authorization server's identifier, matched against `iss` exactly,
    # and this resource server's own identifier, matched against `aud`
    # exactly. Neither has a default and neither may be blank: a validator
    # comparing against an empty string would accept a token that carried one,
    # and the failure would be silent. Refusing to boot is the loud version.
    MCP_OAUTH_ISSUER = os.environ.get('MCP_OAUTH_ISSUER', '').strip()
    MCP_OAUTH_AUDIENCE = os.environ.get('MCP_OAUTH_AUDIENCE', '').strip()
    for _name, _value in (
        ('MCP_OAUTH_ISSUER', MCP_OAUTH_ISSUER),
        ('MCP_OAUTH_AUDIENCE', MCP_OAUTH_AUDIENCE),
    ):
        if not _value:
            raise ImproperlyConfigured(
                f'{_name} must be set when MCP_OAUTH_ENABLED is on. '
                'It is compared against a claim in every token, and comparing '
                'against an empty value would accept tokens meant for someone '
                'else. See docs/configuration.md.'
            )

    # Where the signing keys are published. Defaults to the conventional path
    # under the issuer, which is what every compliant server uses.
    MCP_OAUTH_JWKS_URL = os.environ.get(
        'MCP_OAUTH_JWKS_URL',
        f'{MCP_OAUTH_ISSUER.rstrip("/")}/.well-known/jwks.json',
    )
else:
    # Defined but empty so the module is importable with the flag off. Nothing
    # reads them in that state -- the authentication class is not installed
    # and the metadata route is not registered.
    MCP_OAUTH_ISSUER = ''
    MCP_OAUTH_AUDIENCE = ''
    MCP_OAUTH_JWKS_URL = ''

# How long a fetched key set is trusted. Bounded so a rotation is picked up
# without a restart, and so a poisoned cache cannot persist indefinitely.
MCP_OAUTH_JWKS_CACHE_SECONDS = env_int('MCP_OAUTH_JWKS_CACHE_SECONDS', default=300)

# The claim carrying the Django user's identifier, and the field to look it up
# by. The authorization server delegates login to this application, so `sub` is
# whatever the consent view put there -- the user's primary key by default.
MCP_OAUTH_SUBJECT_CLAIM = os.environ.get('MCP_OAUTH_SUBJECT_CLAIM', 'sub')
MCP_OAUTH_USER_LOOKUP_FIELD = os.environ.get('MCP_OAUTH_USER_LOOKUP_FIELD', 'pk')

# The scope an unsafe method requires. Mirrors the API-key read/write split:
# a token without it is read-only, which is the safe default for a credential
# handed to an agent. Set empty to let any valid token write.
MCP_OAUTH_WRITE_SCOPE = os.environ.get('MCP_OAUTH_WRITE_SCOPE', 'mcp:write')

# Scopes advertised in the protected-resource metadata document, so a client
# knows what to ask the authorization server for.
MCP_OAUTH_SCOPES_SUPPORTED = env_list(
    'MCP_OAUTH_SCOPES_SUPPORTED', default=['mcp:read', 'mcp:write']
)


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
    # How a client with no session says which organization it is acting for.
    # See apps/organizations/context.py. Harmless with ORGANIZATIONS_ENABLED
    # off -- nothing reads it -- and listing it unconditionally keeps the
    # preflight allowance from depending on a flag.
    'x-organization',
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
