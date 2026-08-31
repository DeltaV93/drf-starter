from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of a user, safe to return to that user."""

    display_name = serializers.CharField(source='get_display_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'phone_number',
            'account_type',
            'role',
            'email_verified',
            'date_joined',
        )
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """Fields a user is allowed to change about themselves.

    Deliberately excludes role, account_type and email_verified: those are
    privilege boundaries and must not be settable from a profile form. Email
    is excluded for a different reason -- it is the sign-in identifier, and
    changing it has to re-verify the new address rather than be a PATCH.
    """

    # An account can be created without a handle, so this is where someone
    # picks one up afterwards -- or clears it again by sending "".
    username = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'username')

    def validate_username(self, value):
        if not value:
            return None

        # Same two rules registration applies, for the same reasons: an
        # address-shaped handle could never be signed in with, and uniqueness
        # is case-insensitive because the sign-in lookup is.
        if '@' in value:
            raise serializers.ValidationError(
                'A username cannot contain "@". Sign in with your email address instead.'
            )

        taken = User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError('A user with that username already exists.')

        return value

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data
