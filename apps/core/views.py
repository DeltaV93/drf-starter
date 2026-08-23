from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from utils.api_utils import api_response
from utils.logging_utils import get_logger

from .health import check_database

logger = get_logger(__name__)


class HealthView(APIView):
    """Liveness probe. Answers as long as the process is up.

    In practice HealthCheckMiddleware answers this path first -- it has to,
    to get ahead of the SSL redirect and ALLOWED_HOSTS. This view keeps the
    endpoint in the OpenAPI schema and in reverse(), and stands in if the
    middleware is ever removed.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(summary='Liveness probe', responses={200: None})
    def get(self, request):
        return api_response(data={'status': 'ok'}, message='Service is running.')


class ReadinessView(APIView):
    """Readiness probe. Fails if a dependency the app cannot serve without is down.

    Also normally answered by HealthCheckMiddleware; see HealthView.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(summary='Readiness probe', responses={200: None, 503: None})
    def get(self, request):
        checks = {'database': check_database()}
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


class SPAView(TemplateView):
    """Serve the built single-page app.

    Wired to a catch-all so client-side routes such as /login resolve: those
    paths have no matching file, so WhiteNoise falls through to Django and
    this hands back index.html for the router to take over.

    Only registered when settings.SERVE_SPA is on -- see template/urls.py.
    """

    template_name = 'index.html'
