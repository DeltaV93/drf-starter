from rest_framework import serializers

from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """No `file` field: the path is not something a client should hold.

    Access goes through the download view, which checks who is asking and then
    issues a URL that expires.
    """

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id',
            'purpose',
            'original_name',
            'content_type',
            'size_bytes',
            'visibility',
            'download_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_download_url(self, attachment) -> str:
        request = self.context.get('request')
        from django.urls import reverse

        path = reverse('v1:attachment_download', args=[attachment.pk])
        return request.build_absolute_uri(path) if request else path
