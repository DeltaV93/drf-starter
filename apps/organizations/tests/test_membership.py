"""Ownership, roles and the boundary between tenants."""

import pytest
from django.urls import reverse

from apps.organizations import services
from apps.organizations.models import Membership
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def _add(organization, role=Membership.Role.MEMBER, email=None):
    user = UserFactory(email=email) if email else UserFactory()
    return Membership.objects.create(organization=organization, user=user, role=role)


def test_the_creator_becomes_the_owner(owner_and_org):
    owner, organization = owner_and_org

    membership = Membership.objects.get(organization=organization, user=owner)
    assert membership.role == Membership.Role.OWNER


def test_the_last_owner_cannot_be_removed(owner_and_org):
    """An ownerless organization cannot be administered, billed or cancelled."""
    owner, organization = owner_and_org
    membership = Membership.objects.get(organization=organization, user=owner)

    with pytest.raises(services.OrganizationError):
        services.remove_member(membership=membership)

    assert Membership.objects.filter(pk=membership.pk).exists()


def test_the_last_owner_cannot_be_demoted(owner_and_org):
    owner, organization = owner_and_org
    membership = Membership.objects.get(organization=organization, user=owner)

    with pytest.raises(services.OrganizationError):
        services.change_role(membership=membership, new_role=Membership.Role.MEMBER)

    membership.refresh_from_db()
    assert membership.role == Membership.Role.OWNER


def test_an_owner_can_leave_once_there_is_another(owner_and_org):
    owner, organization = owner_and_org
    _add(organization, role=Membership.Role.OWNER)
    membership = Membership.objects.get(organization=organization, user=owner)

    services.remove_member(membership=membership)

    assert not Membership.objects.filter(pk=membership.pk).exists()
    assert organization.owners.count() == 1


def test_a_member_can_always_be_removed(owner_and_org):
    _owner, organization = owner_and_org
    membership = _add(organization)

    services.remove_member(membership=membership)

    assert not Membership.objects.filter(pk=membership.pk).exists()


def test_the_last_owner_can_be_demoted_after_promoting_someone_else(owner_and_org):
    owner, organization = owner_and_org
    other = _add(organization)
    services.change_role(membership=other, new_role=Membership.Role.OWNER)

    membership = Membership.objects.get(organization=organization, user=owner)
    services.change_role(membership=membership, new_role=Membership.Role.MEMBER)

    membership.refresh_from_db()
    assert membership.role == Membership.Role.MEMBER


def test_a_user_belongs_to_an_organization_only_once(owner_and_org):
    from django.db import IntegrityError

    owner, organization = owner_and_org

    with pytest.raises(IntegrityError):
        Membership.objects.create(organization=organization, user=owner)


# --------------------------------------------------------------------------
# Tenant isolation
# --------------------------------------------------------------------------


def test_a_member_cannot_read_another_organizations_members(sign_in):
    """The whole point of tenancy. Every view scopes to the active org."""
    outsider = UserFactory()
    services.create_organization(name='Theirs', owner=outsider)

    mine_owner = UserFactory()
    services.create_organization(name='Mine', owner=mine_owner)

    client = sign_in(mine_owner)
    response = client.get(reverse('v1:organization_members'))

    assert response.status_code == 200
    emails = {m['email'] for m in response.json()['data']}
    assert emails == {mine_owner.email}
    assert outsider.email not in emails


def test_switching_to_an_organization_you_do_not_belong_to_is_a_404(sign_in):
    outsider = UserFactory()
    theirs = services.create_organization(name='Theirs', owner=outsider)

    mine_owner = UserFactory()
    services.create_organization(name='Mine', owner=mine_owner)

    client = sign_in(mine_owner)
    response = client.post(
        reverse('v1:organization_switch', args=[theirs.slug]), content_type='application/json'
    )

    assert response.status_code == 404


def test_a_plain_member_cannot_invite(owner_and_org, sign_in):
    _owner, organization = owner_and_org
    member = _add(organization)

    client = sign_in(member.user)
    response = client.post(
        reverse('v1:organization_invitations'),
        {'email': 'someone@example.com'},
        content_type='application/json',
    )

    assert response.status_code == 403


def test_a_plain_member_cannot_change_roles(owner_and_org, sign_in):
    _owner, organization = owner_and_org
    member = _add(organization)
    victim = _add(organization)

    client = sign_in(member.user)
    response = client.patch(
        reverse('v1:organization_member_detail', args=[victim.pk]),
        {'role': 'OWNER'},
        content_type='application/json',
    )

    assert response.status_code == 403
    victim.refresh_from_db()
    assert victim.role == Membership.Role.MEMBER


def test_an_admin_cannot_touch_a_member_of_another_organization(sign_in):
    """Scoping is by the session's organization, not by the id in the URL."""
    outsider = UserFactory()
    theirs = services.create_organization(name='Theirs', owner=outsider)
    their_membership = Membership.objects.get(organization=theirs, user=outsider)

    mine_owner = UserFactory()
    services.create_organization(name='Mine', owner=mine_owner)

    client = sign_in(mine_owner)
    response = client.delete(
        reverse('v1:organization_member_detail', args=[their_membership.pk])
    )

    assert response.status_code == 404
    assert Membership.objects.filter(pk=their_membership.pk).exists()


def test_someone_with_no_organization_is_refused_rather_than_served_a_default(sign_in):
    loner = UserFactory()

    client = sign_in(loner)
    response = client.get(reverse('v1:organization_members'))

    assert response.status_code == 403
