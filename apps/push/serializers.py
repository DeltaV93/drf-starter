from rest_framework import serializers

from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id',
            'token',
            'platform',
            'device_name',
            'is_active',
            'last_seen_at',
            'created_at',
        ]
        read_only_fields = ['id', 'is_active', 'last_seen_at', 'created_at']


class DeviceRegistrationSerializer(serializers.Serializer):
    """What the app posts on launch, every launch.

    Registration is deliberately idempotent -- see the view. The client has no
    way to know whether this token is new, so it re-sends it each time rather
    than tracking that itself, and the endpoint absorbs the repetition.
    """

    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=Device.Platform.choices)
    device_name = serializers.CharField(max_length=128, required=False, allow_blank=True)
