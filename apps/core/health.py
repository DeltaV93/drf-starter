"""Health probe logic, shared by the middleware and the documented views."""

from django.db import connection

from utils.logging_utils import get_logger

logger = get_logger(__name__)

# Kept in sync with apps/core/urls.py. The middleware matches on the literal
# path because it runs before URL resolution.
LIVENESS_PATH = '/api/v1/health/'
READINESS_PATH = '/api/v1/ready/'


def check_database():
    """True if the default database answers a trivial query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        logger.exception('Database readiness check failed')
        return False
    return True
