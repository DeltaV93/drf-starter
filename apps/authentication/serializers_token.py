"""Request and response shapes for the bearer-token endpoints.

Declared rather than inferred: `spectacular --fail-on-warn` runs in CI and in
`make check`, and it cannot guess the body of a plain APIView.
"""

from rest_framework import serializers

from apps.users.serializers import UserSerializer


class TokenObtainSerializer(serializers.Serializer):
    """Same credentials the session login takes."""

    identifier = serializers.CharField(
        max_length=255,
        help_text='Email address, or username for an account that has one.',
    )
    password = serializers.CharField(
        max_length=128, write_only=True, style={'input_type': 'password'}
    )


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenTwoFactorSerializer(serializers.Serializer):
    challenge = serializers.CharField(
        help_text='The value auth/token/ returned alongside two_factor_required.'
    )
    code = serializers.CharField(max_length=64)


class TokenPairSerializer(serializers.Serializer):
    """What a completed token sign-in hands back.

    `access`, `refresh` and `user` are absent when `two_factor_required` is
    true -- the password was right, but nothing is authenticated yet. A client
    that reads `access` unconditionally stores `undefined` and believes itself
    signed in, which is worse than failing, so branch on the flag.
    """

    access = serializers.CharField(read_only=True, required=False)
    refresh = serializers.CharField(read_only=True, required=False)
    access_expires_in = serializers.IntegerField(
        read_only=True,
        required=False,
        help_text='Seconds until `access` expires. Refresh before then.',
    )
    user = UserSerializer(read_only=True, required=False)
    two_factor_required = serializers.BooleanField(read_only=True, required=False)
    challenge = serializers.CharField(
        read_only=True,
        required=False,
        help_text='Present with two_factor_required. Post it back to auth/token/2fa/verify/.',
    )
    method = serializers.CharField(
        read_only=True,
        required=False,
        help_text='Which second factor was accepted: "totp" or "recovery".',
    )
