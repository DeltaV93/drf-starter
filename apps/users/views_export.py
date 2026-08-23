"""Requesting and downloading a data export.

Portability, the other half of the erasure in utils/gdpr_utils.py. No feature
flag: a template should not ship half a regulation.
"""

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from utils.api_utils import api_response
from utils.gdpr_tasks import export_json_for, read_download_token, request_export


class DataExportRateThrottle(UserRateThrottle):
    """Building an export walks every table this user touches.

    Tight on purpose: it is expensive, and it sends mail to an address, so an
    unthrottled version is both a load amplifier and a way to have the
    application send someone repeated email.
    """

    scope = 'data_export'


class DataExportRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [DataExportRateThrottle]

    @extend_schema(summary='Request a copy of your data', request=None, responses={202: None})
    def post(self, request):
        request_export(request.user)
        # Delivered by email rather than in the response: the link has to
        # reach the account's own address, not merely whoever is holding the
        # session that asked.
        return api_response(
            message='Your export is being prepared. Check your email for the link.',
            status_code=status.HTTP_202_ACCEPTED,
        )


class DataExportDownloadView(APIView):
    """Serve an export against a signed, expiring token.

    AllowAny because the token is the credential -- it is emailed to the
    account's own address and it ages out. Requiring a session as well would
    stop the link working in whatever browser opened the mail.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [DataExportRateThrottle]

    @extend_schema(summary='Download an export', responses={200: None})
    def get(self, request, token):
        from django.contrib.auth import get_user_model

        user_id = read_download_token(token)
        if user_id is None:
            return api_response(
                message='That link is not valid or has expired. Request a new export.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return api_response(
                message='That link is not valid or has expired. Request a new export.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        response = HttpResponse(export_json_for(user), content_type='application/json')
        # Content-Disposition, so a browser saves it rather than rendering a
        # page's worth of someone's personal data in a tab.
        response['Content-Disposition'] = 'attachment; filename="data-export.json"'
        # Not cacheable anywhere: this is personal data behind a URL that will
        # sit in a mail client's history.
        response['Cache-Control'] = 'no-store, private'
        return response
