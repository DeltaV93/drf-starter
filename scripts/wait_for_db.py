"""Block until the database accepts a connection.

Kept in one process rather than re-running `django.setup()` per attempt: that
cost a second or two of interpreter startup on every retry, so DB_WAIT_ATTEMPTS
meant roughly three times as long as it read.

The error is printed on the first failure, not only after the last one. A
container that sits silent for ninety seconds and then dies looks to the
platform like a port that never opened, which sends whoever is reading the
deploy log after the wrong problem.
"""

import os
import sys
import time
from pathlib import Path

# Running a script puts its own directory on sys.path, not the working
# directory, so the project package is not importable without this. manage.py
# needs no equivalent because it sits at the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

# Same default as manage.py, so this runs from a plain shell as well as from
# the container, where the Dockerfile already exports it.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'template.settings')

django.setup()

from django.conf import settings  # noqa: E402  (needs django.setup() first)
from django.db import connections  # noqa: E402

db = settings.DATABASES['default']
print(
    f'Waiting for the database at {db.get("HOST") or "default"}:'
    f'{db.get("PORT") or "default"} (name={db.get("NAME")})...',
    flush=True,
)

attempts = int(os.environ.get('DB_WAIT_ATTEMPTS') or 30)
last_error = None

for attempt in range(1, attempts + 1):
    try:
        connections['default'].ensure_connection()
    except Exception as exc:  # any driver error means not ready yet
        last_error = exc
        # First failure, then every fifth, then the last one. Enough to see
        # what is wrong without a hundred identical lines.
        if attempt == 1 or attempt % 5 == 0 or attempt == attempts:
            print(f'  attempt {attempt}/{attempts}: {exc}', file=sys.stderr, flush=True)
        connections['default'].close()
        time.sleep(1)
    else:
        print('Database is up.', flush=True)
        sys.exit(0)

print(
    f'Database did not become available after {attempts} attempts: {last_error}',
    file=sys.stderr,
    flush=True,
)
sys.exit(1)
