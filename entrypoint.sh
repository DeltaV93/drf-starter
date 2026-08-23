#!/bin/sh
set -e

# Wait for the database before doing anything that needs it. Compose starts
# containers in dependency order but does not wait for Postgres to finish
# initialising, so the first migrate would otherwise race it.
if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
    echo "Waiting for database at ${DB_HOST:-localhost}:${DB_PORT:-5432}..."
    attempts=0
    max_attempts="${DB_WAIT_ATTEMPTS:-30}"
    until python -c "
import os, sys
import psycopg
try:
    psycopg.connect(
        dbname=os.environ.get('DB_NAME', 'app'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        connect_timeout=2,
    ).close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge "$max_attempts" ]; then
            echo "Database did not become available after ${max_attempts} attempts." >&2
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
