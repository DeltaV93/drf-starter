"""Project package.

Importing the Celery app here means shared_task picks up the right app no
matter how the process was started.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
