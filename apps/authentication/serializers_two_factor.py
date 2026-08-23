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
