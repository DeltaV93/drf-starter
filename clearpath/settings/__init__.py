"""Environment-aware settings loader.

Two ways to select settings, both supported:

1. ``DJANGO_SETTINGS_MODULE=clearpath.settings`` plus ``DJANGO_ENVIRONMENT``
   (development | production | testing). This is what manage.py, wsgi.py,
   asgi.py and celery.py default to.
2. ``DJANGO_SETTINGS_MODULE=clearpath.settings.production`` -- name the
   environment module directly. This is what pytest and CI do.

The guard below matters: importing ``clearpath.settings.testing`` also imports
this package first, and without it that would load the *development*
environment as a side effect before testing.py ever ran.
"""

import os

_SETTINGS_MODULE = os.environ.get('DJANGO_SETTINGS_MODULE', '')

if _SETTINGS_MODULE in ('', 'clearpath.settings'):
    _ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'development').lower()

    if _ENVIRONMENT == 'production':
        from .production import *
    elif _ENVIRONMENT == 'testing':
        from .testing import *
    else:
        from .development import *
