from django.utils import timezone
from rest_framework import serializers

from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    """A key as it appears in a listing.

    There is no field for the secret, and there cannot be one: only a digest
    is stored. The prefix identifies the key without revealing anything.
    """

    is_expired = serializers.BooleanField(read_only=True)
    is_revoked = serializers.BooleanField(read_only=True)

    class Meta:
        model = APIKey
        fields = [
            'id',
            'name',
            'prefix',
            'scope',
            'expires_at',
            'revoked_at',
            'last_used_at',
            'created_at',
            'is_expired',
            'is_revoked',
        ]
        read_only_fields = fields


class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    scope = serializers.ChoiceField(choices=APIKey.Scope.choices, default=APIKey.Scope.READ)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError(
                'An expiry in the past would make the key useless.'
            )
        return value
