from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            'id',
            'action',
            'actor_label',
            'target',
            'ip_address',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields
