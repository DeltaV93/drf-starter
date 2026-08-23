from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from utils.api_utils import api_response
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class HealthView(APIView):
    """Liveness probe. Answers as long as the process is up."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(summary='Liveness probe', responses={200: None})
    def get(self, request):
        return api_response(data={'status': 'ok'}, message='Service is running.')


class ReadinessView(APIView):
    """Readiness probe. Fails if a dependency the app cannot serve without is down."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(summary='Readiness probe', responses={200: None, 503: None})
    def get(self, request):
        checks = {'database': self._check_database()}
        healthy = all(checks.values())

        if not healthy:
            logger.error('Readiness check failed: %s', checks)

        return api_response(
            data={'checks': checks},
            message='Ready.' if healthy else 'One or more dependencies are unavailable.',
            status_code=(
                status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
        )

    @staticmethod
    def _check_database():
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            logger.exception('Database readiness check failed')
            return False
        return True
