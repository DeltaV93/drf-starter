"""Telling a mobile client whether it is too old to run.

Unauthenticated on purpose. A blocked build has to be told so *before* anyone
signs in -- the whole point is that it may be a build whose sign-in is what
broke. It reveals nothing but the version floor its own store listing implies.
"""

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from utils.api_utils import api_response

from .models import AppRelease
from .serializers import UpgradeCheckQuerySerializer, UpgradeCheckSerializer
from .versions import requirement_for

# Long enough that a cold start does not cost a query, short enough that
# raising a floor during an incident reaches devices within minutes.
CACHE_SECONDS = 60


# What an unconfigured platform answers, and the shape everything else fills
# in. A platform with no row is the ordinary case, not an error.
NO_CONSTRAINT = {
    'minimum_version': '',
    'recommended_version': '',
    'store_url': '',
    'message': '',
}


def _floors_for(platform: str) -> dict[str, str]:
    """The row's fields, cached.

    Fields rather than the model instance: a cached `AppRelease` is a pickled
    object, and one that outlives a migration adding or removing a field comes
    back from the cache unable to be read. Four strings cannot.
    """
    key = f'app_release:{platform}'
    cached = cache.get(key)
    if cached is None:
        row = AppRelease.objects.filter(platform=platform).only(*NO_CONSTRAINT).first()
        cached = (
            dict(NO_CONSTRAINT)
            if row is None
            else {field: getattr(row, field) for field in NO_CONSTRAINT}
        )
        cache.set(key, cached, CACHE_SECONDS)
    return cached


class UpgradeCheckView(APIView):
    """`GET /app/upgrade/?platform=ios&version=1.4.0`"""

    permission_classes = [AllowAny]

    # Its own throttle, replacing the default classes rather than adding to
    # them. The default anonymous rate is a daily budget sized for a person
    # browsing; this is called by every installation on every launch, and
    # anonymous throttling is keyed by IP -- so one office behind one NAT
    # would exhaust a day's allowance in a morning and the gate would stop
    # answering for everyone there. It reads a value cached for a minute, so
    # a generous ceiling costs almost nothing.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'app_upgrade'

    @extend_schema(
        summary='Ask whether this build of the mobile app may still run',
        parameters=[
            UpgradeCheckQuerySerializer,
            OpenApiParameter(
                name='version',
                description="The build's own version, as the store shows it. Example: 1.4.0",
                required=True,
                type=str,
            ),
        ],
        responses={200: UpgradeCheckSerializer, 400: None},
        auth=[],
    )
    def get(self, request):
        query = UpgradeCheckQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return api_response(
                errors=query.errors,
                message='Tell us the platform and version to check.',
                status_code=400,
            )

        platform = query.validated_data['platform']
        version = query.validated_data['version']
        floors = _floors_for(platform)

        payload = {
            **floors,
            'requirement': requirement_for(
                version, floors['minimum_version'], floors['recommended_version']
            ),
        }

        return api_response(
            data=UpgradeCheckSerializer(payload).data,
            message='Version checked.',
        )
