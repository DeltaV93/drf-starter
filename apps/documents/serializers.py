from rest_framework import serializers
from .models import DocumentVault, Document, DocumentVersion


class DocumentVaultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVault
        fields = ['id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateVaultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVault
        fields = ['key_derivation_salt', 'encrypted_master_key', 'master_key_nonce']


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ['id', 'version_number', 'uploaded_at', 'storage_path']


class DocumentSerializer(serializers.ModelSerializer):
    versions = DocumentVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'category', 'storage_path', 'file_size',
            'mime_type', 'created_at', 'updated_at', 'versions'
        ]


class CreateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['filename', 'category', 'encrypted_file_key', 'storage_path', 'file_size', 'mime_type']
