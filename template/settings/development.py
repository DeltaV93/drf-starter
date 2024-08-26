# dev.py
from .base import *

DEBUG = True

# Add any development-specific settings here
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'host.docker.internal']

# You might want to use a local database for development
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Disable caching in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Add Django Debug Toolbar for development
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']

# EMAIL
EMAIL_BACKEND = 'django_ses.SESBackend'

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = os.getenv("AWS_SES_REGION_NAME")
AWS_SES_REGION_ENDPOINT = f'email.{AWS_SES_REGION_NAME}.amazonaws.com'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

# CORS ISSUES
# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://host.docker.internal:3000",
    "https://host.docker.internal:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    # "https://yourdomain.com",
]
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'https://localhost:3000',
    'http://127.0.0.1:3000',
    'https://127.0.0.1:3000',
]
CORS_ALLOW_HEADERS = [
    'content-type',
    'authorization',
    'x-requested-with',
    'accept',
    'origin',
    'x-csrftoken',
]
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']

# HTTPS settings
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# CSRF_USE_SESSIONS = True
# CSRF_COOKIE_HTTPONLY = False

# SSL certificate paths
# SSL_CERTIFICATE = os.path.join(BASE_DIR, '../../localhost.crt')
# SSL_KEY = os.path.join(BASE_DIR, '../../localhost.key')

# CSRF_COOKIE_NAME = 'csrftoken'
# CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'