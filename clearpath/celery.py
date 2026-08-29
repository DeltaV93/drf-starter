import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clearpath.settings')

app = Celery('clearpath')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Autodiscovery only walks INSTALLED_APPS, and `utils` is a plain package
# rather than an app, so its tasks need naming explicitly. Without this the
# email task registers in the web process (which imports it directly) but not
# in the worker, and every queued message dies as an unregistered task.
app.autodiscover_tasks(['utils'], related_name='tasks')


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Smoke test that the worker is picking up tasks.

    Call it with `debug_task.delay()` from `manage.py shell`.
    """
    print(f'Request: {self.request!r}')
