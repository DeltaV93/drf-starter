from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from utils.api_utils import api_response
from .models import DocumentVault, Document
from .serializers import DocumentVaultSerializer, CreateVaultSerializer, DocumentSerializer, CreateDocumentSerializer


class VaultCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Create document vault',
        request=CreateVaultSerializer,
        responses={201: DocumentVaultSerializer},
    )
    def post(self, request):
        # Check if vault already exists
        vault, created = DocumentVault.objects.get_or_create(
            user=request.user,
            defaults={
                'key_derivation_salt': request.data.get('key_derivation_salt', b''),
                'encrypted_master_key': request.data.get('encrypted_master_key', b''),
                'master_key_nonce': request.data.get('master_key_nonce', b''),
            }
        )

        if not created:
            return api_response(
                message='Vault already exists for this user',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(data=DocumentVaultSerializer(vault).data, status_code=status.HTTP_201_CREATED)


class VaultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get vault details',
        responses=DocumentVaultSerializer,
    )
    def get(self, request):
        vault = get_object_or_404(DocumentVault, user=request.user)
        return api_response(data=DocumentVaultSerializer(vault).data)


class DocumentsListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List documents',
        responses=DocumentSerializer(many=True),
    )
    def get(self, request):
        vault = get_object_or_404(DocumentVault, user=request.user)
        docs = vault.documents.all().prefetch_related('versions')
        return api_response(data=DocumentSerializer(docs, many=True).data)

    @extend_schema(
        summary='Create document',
        request=CreateDocumentSerializer,
        responses={201: DocumentSerializer},
    )
    def post(self, request):
        vault = get_object_or_404(DocumentVault, user=request.user)
        serializer = CreateDocumentSerializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        doc = serializer.save(vault=vault)
        return api_response(data=DocumentSerializer(doc).data, status_code=status.HTTP_201_CREATED)


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get document details',
        responses=DocumentSerializer,
    )
    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, vault__user=request.user)
        return api_response(data=DocumentSerializer(doc).data)

    @extend_schema(
        summary='Delete document',
        responses={204: None},
    )
    def delete(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, vault__user=request.user)
        doc.delete()
        return api_response(message='Document deleted', status_code=status.HTTP_204_NO_CONTENT)
