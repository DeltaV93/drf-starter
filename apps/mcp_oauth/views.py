"""Publishing where this resource server's authorization server is.

One endpoint, no state, no credential required -- a client has to be able to
read it *before* it has a token, which is the whole point of it.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .metadata import document
from .serializers import ProtectedResourceMetadataSerializer


class ProtectedResourceMetadataView(APIView):
    # No authentication classes at all, rather than AllowAny alone: leaving
    # the defaults in place would run SessionAuthentication and its CSRF
    # enforcement on a document whose entire purpose is to be readable by a
    # client that has no session and no token.
    authentication_classes = []
    permission_classes = [AllowAny]
    # No throttle either, and that is not laziness.
    #
    # The default AnonRateThrottle reads and writes the cache on every request.
    # This document is static, tiny and identical for every caller, so the
    # round-trip buys nothing -- and it makes discovery fail with a 500 when
    # Redis is down, which was observed rather than theorised. A client that
    # cannot read this document cannot authenticate at all, so it is the last
    # endpoint that should inherit a dependency on the cache being up.
    #
    # It also shares the anonymous budget with the rest of the public API, so
    # a client polling discovery would eat into the budget for login.
    throttle_classes = []

    @extend_schema(
        summary='OAuth protected-resource metadata',
        description=(
            'RFC 9728 discovery. Returns the raw metadata document rather '
            'than the usual `{status, message, data, errors}` envelope, '
            'because a standards-compliant client parses it directly.'
        ),
        request=None,
        responses={200: ProtectedResourceMetadataSerializer},
    )
    def get(self, request):
        return Response(document())
