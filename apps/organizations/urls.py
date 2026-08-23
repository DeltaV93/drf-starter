from django.urls import path

from .views import (
    ActiveOrganizationView,
    InvitationAcceptView,
    InvitationListCreateView,
    InvitationRevokeView,
    LeaveOrganizationView,
    MemberDetailView,
    MemberListView,
    OrganizationDetailView,
    OrganizationListCreateView,
)

urlpatterns = [
    path('organizations/', OrganizationListCreateView.as_view(), name='organization_list'),
    path(
        'organizations/active/', ActiveOrganizationView.as_view(), name='organization_active'
    ),
    path(
        'organizations/active/switch/<slug:slug>/',
        ActiveOrganizationView.as_view(),
        name='organization_switch',
    ),
    path(
        'organizations/current/', OrganizationDetailView.as_view(), name='organization_detail'
    ),
    path(
        'organizations/current/members/', MemberListView.as_view(), name='organization_members'
    ),
    path(
        'organizations/current/members/<int:member_id>/',
        MemberDetailView.as_view(),
        name='organization_member_detail',
    ),
    path(
        'organizations/current/leave/',
        LeaveOrganizationView.as_view(),
        name='organization_leave',
    ),
    path(
        'organizations/current/invitations/',
        InvitationListCreateView.as_view(),
        name='organization_invitations',
    ),
    path(
        'organizations/current/invitations/<int:invitation_id>/',
        InvitationRevokeView.as_view(),
        name='organization_invitation_revoke',
    ),
    path(
        'organizations/invitations/accept/',
        InvitationAcceptView.as_view(),
        name='organization_invitation_accept',
    ),
]
