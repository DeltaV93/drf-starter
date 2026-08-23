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
    python scripts/wait_for_db.py
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --noinput
fi

# No-op unless all three DJANGO_SUPERUSER_* variables are set.
python manage.py create_superuser_if_not_exists

exec "$@"
