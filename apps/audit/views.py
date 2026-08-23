"""Reading the audit log.

Scoped to the caller's own events. There is no endpoint that returns everybody's
-- staff read the admin, which is authenticated and access-controlled
separately, rather than through an API surface a stolen session could reach.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from .models import AuditEvent
from .serializers import AuditEventSerializer


class MyAuditLogView(APIView):
    """The events recorded against the signed-in user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Your recent account activity',
        responses={200: AuditEventSerializer(many=True)},
    )
    def get(self, request):
        events = AuditEvent.objects.filter(actor=request.user)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(events, request, view=self)

        return api_response(
            data={
                'results': AuditEventSerializer(page, many=True).data,
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
            },
            message='Activity retrieved.',
        )
