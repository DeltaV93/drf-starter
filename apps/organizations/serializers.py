from rest_framework import serializers

from .models import Invitation, Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'role', 'member_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def get_role(self, organization) -> str | None:
        """The requesting user's role, when the view supplied it.

        Null on a listing that did not resolve memberships -- the field says
        "your role here", and inventing one would be worse than omitting it.
        """
        roles = self.context.get('roles_by_org_id') or {}
        return roles.get(organization.pk)

    def get_member_count(self, organization) -> int:
        return organization.memberships.count()


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_last_owner = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_last_owner',
            'created_at',
        ]
        read_only_fields = fields


class MemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class InvitationSerializer(serializers.ModelSerializer):
    """What an invitation looks like to an administrator.

    Deliberately has no token field. The raw token exists only in the email --
    exposing it here would let any admin, or anyone who could read one API
    response, accept on someone else's behalf.
    """

    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            'id',
            'email',
            'role',
            'invited_by_email',
            'expires_at',
            'is_expired',
            'created_at',
        ]
        read_only_fields = fields


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=Membership.Role.choices, default=Membership.Role.MEMBER
    )


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()


class ActiveOrganizationSerializer(serializers.Serializer):
    """`organization` is null when the caller belongs to none, which is not
    an error -- a user with no team is the ordinary starting state."""

    organization = OrganizationSerializer(read_only=True, allow_null=True)
