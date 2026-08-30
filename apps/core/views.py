from django.http import Http404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.api_utils import api_response
from utils.logging_utils import get_logger

from . import deep_links
from .health import check_database
from .serializers import AppleAppSiteAssociationSerializer, AssetLinkSerializer

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


class _AssociationDocumentView(APIView):
    """Shared setup for the two mobile association documents.

    No authentication classes at all, rather than AllowAny alone: leaving the
    defaults in place would run SessionAuthentication and its CSRF enforcement
    on a document whose entire purpose is to be fetched by Apple's and
    Google's crawlers, which have no session and no token.

    No throttle either, for the reason apps/mcp_oauth's metadata view records:
    the default throttle reads and writes the cache on every request, and
    these documents are static, tiny and identical for every caller. A 500
    because Redis is down would mean links silently stop opening the app.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []


class AppleAppSiteAssociationView(_AssociationDocumentView):
    """`/.well-known/apple-app-site-association`.

    404s until MOBILE_IOS_APP_ID is set, which is the honest answer for a
    deployment with no iOS app -- an empty document published at this path
    tells the operating system the association was checked and refused, and
    that answer is cached.
    """

    @extend_schema(
        summary='Apple app-site association',
        description=(
            'Returns the raw association document rather than the usual '
            '`{status, message, data, errors}` envelope: the shape is fixed by '
            'Apple and parsed by the operating system, not by this project. '
            '404s when no iOS app is configured.'
        ),
        request=None,
        responses={200: AppleAppSiteAssociationSerializer, 404: None},
    )
    def get(self, request):
        if not deep_links.ios_configured():
            raise Http404
        return Response(deep_links.apple_app_site_association())


class AssetLinksView(_AssociationDocumentView):
    """`/.well-known/assetlinks.json`.

    404s until both the Android package and at least one signing fingerprint
    are set: a target naming a package with no fingerprint verifies nothing,
    and Android treats the whole document as invalid rather than ignoring the
    bad entry.
    """

    @extend_schema(
        summary='Android digital asset links',
        description=(
            'Returns the raw Digital Asset Links array rather than the usual '
            '`{status, message, data, errors}` envelope: the shape is fixed by '
            'Google and parsed by the operating system, not by this project. '
            '404s when no Android app is configured.'
        ),
        request=None,
        responses={200: AssetLinkSerializer(many=True), 404: None},
    )
    def get(self, request):
        if not deep_links.android_configured():
            raise Http404
        return Response(deep_links.asset_links())


class SPAView(TemplateView):
    """Serve the built single-page app.

    Wired to a catch-all so client-side routes such as /login resolve: those
    paths have no matching file, so WhiteNoise falls through to Django and
    this hands back index.html for the router to take over.

    Only registered when settings.SERVE_SPA is on -- see template/urls.py.
    """

    template_name = 'index.html'
