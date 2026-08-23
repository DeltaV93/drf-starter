#!/bin/sh
set -e

# Wait for the database before doing anything that needs it. Compose starts
# containers in dependency order but does not wait for Postgres to finish
# initialising, and managed hosts can attach the database after the app boots.
#
# The check goes through Django's own connection so it honours whatever the
# settings resolved to -- DATABASE_URL on a managed host, the individual DB_*
# variables locally. Re-parsing the connection details here would miss one.
if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
    # Name the target, so a misconfigured host is obvious from the first line
    # rather than only from a traceback 30 attempts later.
    python -c "
import django
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
print(f\"Waiting for the database at {db.get('HOST') or 'default'}:{db.get('PORT') or 'default'}\"
      f\" (name={db.get('NAME')})...\")
" || echo "Waiting for the database..."
    attempts=0
    max_attempts="${DB_WAIT_ATTEMPTS:-30}"
    until python -c "
import django
django.setup()
from django.db import connections
connections['default'].ensure_connection()
" 2>/dev/null; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge "$max_attempts" ]; then
            echo "Database did not become available after ${max_attempts} attempts." >&2
            # Surface the real error rather than exiting on a swallowed one.
            python -c "
import django
django.setup()
from django.db import connections
connections['default'].ensure_connection()
" || true
            exit 1
        fi
        sleep 1
    done
    echo "Database is up."
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --noinput
fi

# No-op unless all three DJANGO_SUPERUSER_* variables are set.
python manage.py create_superuser_if_not_exists

exec "$@"
