from rest_framework import serializers
from .models import ShareLink, ShareLinkDocument, ShareSession
from apps.documents.serializers import DocumentSerializer


class ShareLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareLink
        fields = ['id', 'token', 'expires_at', 'created_at']
        read_only_fields = ['id', 'token', 'created_at']


class CreateShareLinkSerializer(serializers.Serializer):
    document_ids = serializers.ListField(child=serializers.IntegerField())
    password = serializers.CharField(max_length=255, required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class ShareLinkDocumentSerializer(serializers.ModelSerializer):
    document = DocumentSerializer(read_only=True)

    class Meta:
        model = ShareLinkDocument
        fields = ['id', 'document']


class ShareSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareSession
        fields = ['id', 'access_token', 'expires_at', 'created_at']
