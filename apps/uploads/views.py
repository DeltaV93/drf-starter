"""Uploading, listing and fetching files."""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from . import services
from .models import Attachment
from .serializers import AttachmentSerializer


class AttachmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(summary='List your files', responses={200: AttachmentSerializer(many=True)})
    def get(self, request):
        attachments = Attachment.objects.filter(user=request.user)
        purpose = request.query_params.get('purpose')
        if purpose:
            attachments = attachments.filter(purpose=purpose)

        return api_response(
            data=AttachmentSerializer(
                attachments, many=True, context={'request': request}
            ).data,
            message='Files retrieved.',
        )

    @extend_schema(
        summary='Upload a file', request=None, responses={201: AttachmentSerializer}
    )
    def post(self, request):
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return api_response(
                message='No file was sent. Use multipart/form-data with a `file` field.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            attachment = services.store(
                user=request.user,
                uploaded_file=uploaded,
                purpose=request.data.get('purpose', 'general'),
            )
        except ValidationError as exc:
            return api_response(
                message='; '.join(exc.messages),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            data=AttachmentSerializer(attachment, context={'request': request}).data,
            message='File uploaded.',
            status_code=status.HTTP_201_CREATED,
        )


class AttachmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Delete a file', responses={200: None})
    def delete(self, request, attachment_id):
        # Filtered by owner, so someone else's id is a 404 rather than a
        # deletion.
        attachment = get_object_or_404(Attachment, pk=attachment_id, user=request.user)
        services.delete(attachment)
        return api_response(message='File deleted.')


class AttachmentDownloadView(APIView):
    """Hand back a URL for the bytes, after checking who is asking.

    A redirect rather than proxying the file: on S3 the target is a signed URL
    that expires, so the application never becomes the bandwidth path.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Download a file', responses={302: None})
    def get(self, request, attachment_id):
        attachment = get_object_or_404(Attachment, pk=attachment_id)

        # Public files are readable by any signed-in user; private ones only by
        # their owner. Ownership is checked here rather than trusted to an
        # unguessable path, because a URL that leaks stays valid forever.
        if not attachment.is_public and attachment.user_id != request.user.pk:
            return api_response(message='Not found.', status_code=status.HTTP_404_NOT_FOUND)

        return redirect(services.url_for(attachment))
