from rest_framework import serializers


class TwoFactorStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    pending = serializers.BooleanField()
    recovery_codes_remaining = serializers.IntegerField()


class TwoFactorPasswordSerializer(serializers.Serializer):
    """Re-authentication for any change to the second factor."""

    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class TwoFactorCodeSerializer(serializers.Serializer):
    # Wide enough for a 6-digit TOTP or a 10-character recovery code, with
    # room for the spaces or dashes people paste along with them.
    code = serializers.CharField(max_length=32, trim_whitespace=True)


# Response shapes. Declared so the generated schema says what each endpoint
# returns instead of falling back to "unknown" -- these views are plain
# APIViews, so nothing can be inferred from a queryset.


class TwoFactorEnrolmentSerializer(serializers.Serializer):
    """The provisioning URI carries the shared secret, and is returned once."""

    provisioning_uri = serializers.CharField(read_only=True)


class RecoveryCodesSerializer(serializers.Serializer):
    """Shown once at enrolment and once per regeneration. Never re-readable."""

    recovery_codes = serializers.ListField(child=serializers.CharField(), read_only=True)
