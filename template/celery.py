import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'template.settings')

app = Celery('template')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Smoke test: `celery -A template call template.debug_task`."""
    print(f'Request: {self.request!r}')
