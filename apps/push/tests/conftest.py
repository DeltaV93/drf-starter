"""Push registration is opt-in; the app is not installed when the flag is off.

`collect_ignore_glob` rather than a module-level `pytest.skip`: importing the
test module imports the model, and a model whose app is not in INSTALLED_APPS
raises at import time -- before any skip inside the module could run.
"""

from django.conf import settings

collect_ignore_glob = [] if settings.PUSH_ENABLED else ['test_*.py']
