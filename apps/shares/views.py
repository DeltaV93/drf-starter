import secrets
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from utils.api_utils import api_response
from apps.documents.models import DocumentVault, Document
from .models import ShareLink, ShareLinkDocument, ShareSession
from .serializers import ShareLinkSerializer, CreateShareLinkSerializer, ShareLinkDocumentSerializer


class ShareLinksListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List share links',
        responses=ShareLinkSerializer(many=True),
    )
    def get(self, request):
        vault = get_object_or_404(DocumentVault, user=request.user)
        shares = vault.shares.all()
        return api_response(data=ShareLinkSerializer(shares, many=True).data)

    @extend_schema(
        summary='Create share link',
        request=CreateShareLinkSerializer,
        responses={201: ShareLinkSerializer},
    )
    def post(self, request):
        vault = get_object_or_404(DocumentVault, user=request.user)
        serializer = CreateShareLinkSerializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create share link
        token = secrets.token_urlsafe(32)
        password_hash = ''
        if serializer.validated_data.get('password'):
            from django.contrib.auth.hashers import make_password
            password_hash = make_password(serializer.validated_data['password'])

        share_link = ShareLink.objects.create(
            vault=vault,
            token=token,
            password_hash=password_hash,
            expires_at=serializer.validated_data.get('expires_at'),
        )

        # Add documents to share
        document_ids = serializer.validated_data.get('document_ids', [])
        for doc_id in document_ids:
            doc = get_object_or_404(Document, id=doc_id, vault=vault)
            ShareLinkDocument.objects.get_or_create(share_link=share_link, document=doc)

        return api_response(data=ShareLinkSerializer(share_link).data, status_code=status.HTTP_201_CREATED)


class ShareLinkDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Delete share link',
        responses={204: None},
    )
    def delete(self, request, pk):
        share = get_object_or_404(ShareLink, pk=pk, vault__user=request.user)
        share.delete()
        return api_response(message='Share link deleted', status_code=status.HTTP_204_NO_CONTENT)


class ShareAccessView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Access shared documents',
        responses=ShareLinkDocumentSerializer(many=True),
    )
    def get(self, request, token):
        now = timezone.now()
        share = get_object_or_404(
            ShareLink,
            token=token,
        )

        # Check expiration
        if share.expires_at and share.expires_at < now:
            return api_response(
                message='Share link has expired',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        docs = share.share_documents.all()
        return api_response(data=ShareLinkDocumentSerializer(docs, many=True).data)

    @extend_schema(
        summary='Verify share link password',
        request={'type': 'object', 'properties': {'password': {'type': 'string'}}},
        responses=ShareLinkSerializer,
    )
    def post(self, request, token):
        now = timezone.now()
        share = get_object_or_404(
            ShareLink,
            token=token,
        )

        # Check expiration
        if share.expires_at and share.expires_at < now:
            return api_response(
                message='Share link has expired',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Verify password if required
        if share.password_hash:
            password = request.data.get('password')
            if not password:
                return api_response(
                    message='Password required',
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            from django.contrib.auth.hashers import check_password
            if not check_password(password, share.password_hash):
                return api_response(
                    message='Invalid password',
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # Create session
        access_token = secrets.token_urlsafe(32)
        session = ShareSession.objects.create(
            share_link=share,
            access_token=access_token,
            expires_at=now + timedelta(hours=24),
        )

        return api_response(
            data={'access_token': access_token, 'expires_at': session.expires_at.isoformat()},
            status_code=status.HTTP_200_OK,
        )
