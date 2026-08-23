from django.contrib.auth import get_user_model
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
    privilege boundaries and must not be settable from a profile form.
    """

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number')

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data
