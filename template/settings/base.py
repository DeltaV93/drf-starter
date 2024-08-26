# base.py
import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

from utils.logging_utils import get_logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=BASE_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY')

logger = get_logger(__name__)

logger.info("Starting App")

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
    'drf_yasg',
    'corsheaders',
    'django_ses',

    # Local apps
    'apps.users',
    'apps.authentication',
    'apps.subscriptions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'template.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'template.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.CustomUser'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # to disable DRF navigation and that fancy display.
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# Internationalization
LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Social Authentication
AUTHENTICATION_BACKENDS = (
    # TODO: remove this for testing, will add this back
    # 'social_core.backends.google.GoogleOAuth2',
    # 'social_core.backends.linkedin.LinkedinOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = os.environ.get('LINKEDIN_OAUTH2_KEY')
SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = os.environ.get('LINKEDIN_OAUTH2_SECRET')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],  # Change to ['file'] to log to a file
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
    },
}

# Swagger settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

# Stripe settings
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Staticfile Storge
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# # Session
# CORS_ALLOW_CREDENTIALS = True  # set this to true if you're using session over token based auth
# # SESSION_COOKIE_SECURE = False  # Set to True in production
# SESSION_COOKIE_HTTPONLY = True
# # CSRF_COOKIE_SECURE = False  # Set to True in production
# CSRF_COOKIE_HTTPONLY = True  # True in prod
# CSRF_COOKIE_SAMESITE = 'Lax'
#
# # CSRF_USE_SESSIONS = False   # Store CSRF token in a cookie instead of the session
# SESSION_COOKIE_SAMESITE = 'Lax'  # Use 'None' if your frontend is on a different domain
# CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_SECURE = True  # Use only in production
CSRF_COOKIE_SECURE = True  # Use only in production
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SAMESITE = 'None'
CSRF_TRUSTED_ORIGINS = ['https://website.com']
CORS_ALLOWED_ORIGINS = ['https://website.com']
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

# In development, you might want to use:
# SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SECURE = False
# CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']
# CORS_ALLOWED_ORIGINS = ['http://localhost:3000']