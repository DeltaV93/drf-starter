"""Organization endpoints.

Every view acts on the organization the *session* selected, never on an id
from the request, so a caller cannot address an organization they do not
belong to. The member and invitation views additionally require IsOrgAdmin.
"""

from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from . import services
from .context import active_membership, active_organization, set_active_organization
from .models import Invitation, Membership
from .permissions import IsOrgAdmin, IsOrgMember
from .serializers import (
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    MemberRoleSerializer,
    MemberSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)


def _invalid(serializer, message):
    return api_response(
        errors=serializer.errors,
        message=message,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _refused(exc):
    """A broken rule is the caller's mistake, not a server error."""
    return api_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List the organizations you belong to',
        responses={200: OrganizationSerializer(many=True)},
    )
    def get(self, request):
        memberships = Membership.objects.select_related('organization').filter(
            user=request.user
        )
        organizations = [m.organization for m in memberships]
        roles = {m.organization_id: m.role for m in memberships}
        active = active_organization(request)

        return api_response(
            data={
                'organizations': OrganizationSerializer(
                    organizations, many=True, context={'roles_by_org_id': roles}
                ).data,
                'activeOrganizationId': active.pk if active else None,
            },
            message='Organizations retrieved.',
        )

    @extend_schema(
        summary='Create an organization',
        request=OrganizationCreateSerializer,
        responses={201: OrganizationSerializer},
    )
    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not create the organization.')

        organization = services.create_organization(
            name=serializer.validated_data['name'], owner=request.user
        )
        # Creating one switches to it; otherwise the caller would have to make
        # a second request before they could do anything with it.
        set_active_organization(request, organization)

        return api_response(
            data=OrganizationSerializer(
                organization, context={'roles_by_org_id': {organization.pk: 'OWNER'}}
            ).data,
            message='Organization created.',
            status_code=status.HTTP_201_CREATED,
        )


class ActiveOrganizationView(APIView):
    """Read or switch the organization the session is acting for."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Get the active organization', responses={200: None})
    def get(self, request):
        membership = active_membership(request)
        if membership is None:
            return api_response(data={'organization': None}, message='No organization.')

        return api_response(
            data={
                'organization': OrganizationSerializer(
                    membership.organization,
                    context={'roles_by_org_id': {membership.organization_id: membership.role}},
                ).data
            },
            message='Active organization retrieved.',
        )

    @extend_schema(summary='Switch the active organization', request=None)
    def post(self, request, slug):
        # Filtered by membership, so switching to an organization you do not
        # belong to is a 404 rather than a silent success.
        membership = get_object_or_404(
            Membership.objects.select_related('organization'),
            user=request.user,
            organization__slug=slug,
        )
        set_active_organization(request, membership.organization)

        return api_response(
            data=OrganizationSerializer(
                membership.organization,
                context={'roles_by_org_id': {membership.organization_id: membership.role}},
            ).data,
            message='Active organization changed.',
        )


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    @extend_schema(
        summary='Get the active organization', responses={200: OrganizationSerializer}
    )
    def get(self, request):
        membership = active_membership(request)
        return api_response(
            data=OrganizationSerializer(
                membership.organization,
                context={'roles_by_org_id': {membership.organization_id: membership.role}},
            ).data,
            message='Organization retrieved.',
        )

    @extend_schema(
        summary='Rename the active organization', request=OrganizationCreateSerializer
    )
    def patch(self, request):
        self.permission_classes = [IsAuthenticated, IsOrgAdmin]
        self.check_permissions(request)

        serializer = OrganizationCreateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not update the organization.')

        organization = active_organization(request)
        organization.name = serializer.validated_data['name']
        organization.save(update_fields=['name', 'updated_at'])

        return api_response(
            data=OrganizationSerializer(organization).data,
            message='Organization updated.',
        )


class MemberListView(APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    @extend_schema(summary='List members', responses={200: MemberSerializer(many=True)})
    def get(self, request):
        members = Membership.objects.select_related('user').filter(
            organization=active_organization(request)
        )
        return api_response(
            data=MemberSerializer(members, many=True).data,
            message='Members retrieved.',
        )


class MemberDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def _member(self, request, member_id):
        return get_object_or_404(
            Membership.objects.select_related('user'),
            pk=member_id,
            organization=active_organization(request),
        )

    @extend_schema(summary="Change a member's role", request=MemberRoleSerializer)
    def patch(self, request, member_id):
        serializer = MemberRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not change the role.')

        try:
            membership = services.change_role(
                membership=self._member(request, member_id),
                new_role=serializer.validated_data['role'],
            )
        except services.OrganizationError as exc:
            return _refused(exc)

        return api_response(data=MemberSerializer(membership).data, message='Role updated.')

    @extend_schema(summary='Remove a member', responses={200: None})
    def delete(self, request, member_id):
        try:
            services.remove_member(membership=self._member(request, member_id))
        except services.OrganizationError as exc:
            return _refused(exc)

        return api_response(message='Member removed.')


class LeaveOrganizationView(APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    @extend_schema(summary='Leave the active organization', request=None)
    def post(self, request):
        membership = active_membership(request)
        try:
            services.remove_member(membership=membership)
        except services.OrganizationError as exc:
            return _refused(exc)

        request.session.pop('active_organization_id', None)
        return api_response(message='You have left the organization.')


class InvitationListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    @extend_schema(
        summary='List pending invitations', responses={200: InvitationSerializer(many=True)}
    )
    def get(self, request):
        invitations = Invitation.objects.select_related('invited_by').filter(
            organization=active_organization(request), accepted_at__isnull=True
        )
        return api_response(
            data=InvitationSerializer(invitations, many=True).data,
            message='Invitations retrieved.',
        )

    @extend_schema(summary='Invite someone', request=InvitationCreateSerializer)
    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not send the invitation.')

        try:
            invitation, _raw_token = services.invite_member(
                organization=active_organization(request),
                email=serializer.validated_data['email'],
                role=serializer.validated_data['role'],
                invited_by=request.user,
                accept_url_template=f'{settings.FRONTEND_URL}/invitations/{{token}}',
            )
        except services.OrganizationError as exc:
            return _refused(exc)

        # The raw token is deliberately absent from the response. It exists
        # only in the email that was just sent.
        return api_response(
            data=InvitationSerializer(invitation).data,
            message='Invitation sent.',
            status_code=status.HTTP_201_CREATED,
        )


class InvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    @extend_schema(summary='Revoke a pending invitation', responses={200: None})
    def delete(self, request, invitation_id):
        invitation = get_object_or_404(
            Invitation,
            pk=invitation_id,
            organization=active_organization(request),
            accepted_at__isnull=True,
        )
        invitation.delete()
        return api_response(message='Invitation revoked.')


class InvitationAcceptView(APIView):
    """Redeem an invitation token.

    Authenticated on purpose: the invitation binds to an email address, and
    without a signed-in user there is nobody to check it against.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Accept an invitation', request=InvitationAcceptSerializer)
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not accept the invitation.')

        try:
            membership = services.accept_invitation(
                raw_token=serializer.validated_data['token'], user=request.user
            )
        except services.OrganizationError as exc:
            return _refused(exc)

        set_active_organization(request, membership.organization)

        return api_response(
            data=OrganizationSerializer(
                membership.organization,
                context={'roles_by_org_id': {membership.organization_id: membership.role}},
            ).data,
            message='Invitation accepted.',
            status_code=status.HTTP_201_CREATED,
        )
