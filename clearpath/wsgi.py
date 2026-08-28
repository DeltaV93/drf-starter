"""WSGI config.

Exposes the WSGI callable as a module-level variable named ``application``.
The settings module is the environment-aware loader, not a concrete
environment -- set DJANGO_ENVIRONMENT to choose.

https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'template.settings')

application = get_wsgi_application()
