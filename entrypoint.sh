#!/bin/sh

# Print database connection settings for debugging
echo "Running started thing"

# Run migrations
python manage.py migrate
echo "======== RAN MIGRATIONS ==========="


# Run the main container command
exec "$@"
