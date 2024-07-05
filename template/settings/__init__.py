# myproject/settings/__init__.py

import os
from .base import *

environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
else:
    from .development import *