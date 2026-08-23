"""The organization endpoints as a client sees them."""

import pytest
from django.urls import reverse

from apps.organizations import services
from apps.organizations.context import SESSION_KEY
from apps.organizations.models import Membership
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_creating_an_organization_switches_to_it(sign_in):
    user = UserFactory()
    client = sign_in(user)

    response = client.post(
        reverse('v1:organization_list'), {'name': 'New Co'}, content_type='application/json'
    )

    assert response.status_code == 201, response.content
    body = response.json()['data']
    assert body['name'] == 'New Co'
    assert body['role'] == 'OWNER'
    # Acting on it immediately, without a second request to select it.
    assert client.session[SESSION_KEY] == body['id']


def test_listing_returns_only_your_own_organizations(sign_in):
    mine_owner = UserFactory()
    services.create_organization(name='Mine', owner=mine_owner)
    services.create_organization(name='Theirs', owner=UserFactory())

    client = sign_in(mine_owner)
    response = client.get(reverse('v1:organization_list'))

    assert response.status_code == 200
    names = {o['name'] for o in response.json()['data']['organizations']}
    assert names == {'Mine'}


def test_a_user_with_one_organization_never_has_to_choose_it(sign_in, owner_and_org):
    """No session key set, yet the endpoints still resolve."""
    owner, organization = owner_and_org
    client = sign_in(owner)
    assert SESSION_KEY not in client.session

    response = client.get(reverse('v1:organization_detail'))

    assert response.status_code == 200
    assert response.json()['data']['name'] == organization.name


def test_switching_changes_which_organization_the_endpoints_answer_for(sign_in):
    user = UserFactory()
    first = services.create_organization(name='First', owner=user)
    second = services.create_organization(name='Second', owner=user)

    client = sign_in(user)
    client.post(reverse('v1:organization_switch', args=[second.slug]))
    response = client.get(reverse('v1:organization_detail'))

    assert response.json()['data']['slug'] == second.slug
    assert response.json()['data']['slug'] != first.slug


def test_a_stale_active_organization_falls_back_rather_than_erroring(sign_in, owner_and_org):
    """Left the organization, or it was deleted, while the session lived on."""
    owner, organization = owner_and_org
    client = sign_in(owner)
    session = client.session
    session[SESSION_KEY] = 999999
    session.save()

    response = client.get(reverse('v1:organization_detail'))

    assert response.status_code == 200
    assert response.json()['data']['slug'] == organization.slug


def test_renaming_needs_admin(owner_and_org, sign_in):
    _owner, organization = owner_and_org
    member = Membership.objects.create(organization=organization, user=UserFactory())

    client = sign_in(member.user)
    response = client.patch(
        reverse('v1:organization_detail'), {'name': 'Renamed'}, content_type='application/json'
    )

    assert response.status_code == 403
    organization.refresh_from_db()
    assert organization.name != 'Renamed'


def test_an_owner_can_rename(owner_and_org, sign_in):
    owner, organization = owner_and_org

    client = sign_in(owner)
    response = client.patch(
        reverse('v1:organization_detail'), {'name': 'Renamed'}, content_type='application/json'
    )

    assert response.status_code == 200
    organization.refresh_from_db()
    assert organization.name == 'Renamed'


def test_leaving_clears_the_active_organization(owner_and_org, sign_in):
    _owner, organization = owner_and_org
    member = Membership.objects.create(organization=organization, user=UserFactory())

    client = sign_in(member.user)
    response = client.post(reverse('v1:organization_leave'))

    assert response.status_code == 200
    assert not Membership.objects.filter(pk=member.pk).exists()
    assert SESSION_KEY not in client.session


def test_the_last_owner_leaving_is_refused_with_a_usable_message(owner_and_org, sign_in):
    owner, _organization = owner_and_org

    client = sign_in(owner)
    response = client.post(reverse('v1:organization_leave'))

    assert response.status_code == 400
    assert 'owner' in response.json()['message'].lower()


def test_anonymous_callers_are_refused(client):
    response = client.get(reverse('v1:organization_list'))

    assert response.status_code in (401, 403)


def test_revoking_an_invitation_removes_it(owner_and_org, sign_in):
    owner, organization = owner_and_org
    invitation, _token = services.invite_member(
        organization=organization,
        email='invitee@example.com',
        role=Membership.Role.MEMBER,
        invited_by=owner,
        accept_url_template='https://app.example.com/invitations/{token}',
    )

    client = sign_in(owner)
    response = client.delete(
        reverse('v1:organization_invitation_revoke', args=[invitation.pk])
    )

    assert response.status_code == 200
    assert not organization.invitations.exists()
