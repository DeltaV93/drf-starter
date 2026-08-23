"""Invitations: the token, the binding, and the seat limit.

An invitation is a bearer credential that grants access to another tenant's
data, so most of what matters here is what it refuses.
"""

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.organizations import services
from apps.organizations.models import Invitation, Membership, hash_invitation_token
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

ACCEPT_TEMPLATE = 'https://app.example.com/invitations/{token}'


def _invite(organization, inviter, email='invitee@example.com', role=Membership.Role.MEMBER):
    return services.invite_member(
        organization=organization,
        email=email,
        role=role,
        invited_by=inviter,
        accept_url_template=ACCEPT_TEMPLATE,
    )


def test_the_raw_token_is_never_stored(owner_and_org):
    """A database dump, a backup or a stray log must not yield a usable token."""
    owner, organization = owner_and_org

    invitation, raw_token = _invite(organization, owner)

    assert raw_token
    assert invitation.token_hash != raw_token
    assert invitation.token_hash == hash_invitation_token(raw_token)
    # And nothing anywhere on the row contains it.
    stored = Invitation.objects.filter(pk=invitation.pk).values().first()
    assert raw_token not in str(stored)


def test_the_token_reaches_the_invitee_only_by_email(owner_and_org):
    owner, organization = owner_and_org

    _invitation, raw_token = _invite(organization, owner)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['invitee@example.com']
    assert raw_token in mail.outbox[0].body


def test_the_api_response_does_not_leak_the_token(owner_and_org, sign_in):
    """Any admin could otherwise accept on the invitee's behalf."""
    owner, _organization = owner_and_org
    client = sign_in(owner)

    response = client.post(
        reverse('v1:organization_invitations'),
        {'email': 'invitee@example.com', 'role': 'MEMBER'},
        content_type='application/json',
    )

    assert response.status_code == 201, response.content
    body = response.json()
    raw_token = Invitation.objects.get().token_hash
    assert 'token' not in str(body)
    assert raw_token not in str(body)


def test_an_invitation_is_bound_to_the_address_it_was_sent_to(owner_and_org):
    """A forwarded or leaked email must not let whoever opens it in first."""
    owner, organization = owner_and_org
    _invitation, raw_token = _invite(organization, owner)
    someone_else = UserFactory(email='someone-else@example.com')

    with pytest.raises(services.OrganizationError):
        services.accept_invitation(raw_token=raw_token, user=someone_else)

    assert not Membership.objects.filter(user=someone_else).exists()


def test_an_invitation_can_only_be_used_once(owner_and_org):
    owner, organization = owner_and_org
    _invitation, raw_token = _invite(organization, owner)
    invitee = UserFactory(email='invitee@example.com')

    services.accept_invitation(raw_token=raw_token, user=invitee)

    with pytest.raises(services.OrganizationError):
        services.accept_invitation(raw_token=raw_token, user=invitee)


def test_an_expired_invitation_is_refused(owner_and_org):
    owner, organization = owner_and_org
    invitation, raw_token = _invite(organization, owner)
    invitation.expires_at = timezone.now() - timezone.timedelta(seconds=1)
    invitation.save(update_fields=['expires_at'])
    invitee = UserFactory(email='invitee@example.com')

    with pytest.raises(services.OrganizationError):
        services.accept_invitation(raw_token=raw_token, user=invitee)

    assert not Membership.objects.filter(user=invitee).exists()


def test_an_unknown_token_is_refused_the_same_way_as_a_spent_one(owner_and_org):
    """Probing tokens must not reveal which ones exist."""
    owner, organization = owner_and_org
    _invitation, raw_token = _invite(organization, owner)
    invitee = UserFactory(email='invitee@example.com')
    services.accept_invitation(raw_token=raw_token, user=invitee)

    with pytest.raises(services.OrganizationError) as spent:
        services.accept_invitation(raw_token=raw_token, user=invitee)
    with pytest.raises(services.OrganizationError) as unknown:
        services.accept_invitation(raw_token='not-a-real-token', user=invitee)

    assert str(spent.value) == str(unknown.value)


def test_accepting_creates_the_membership_with_the_invited_role(owner_and_org):
    owner, organization = owner_and_org
    _invitation, raw_token = _invite(organization, owner, role=Membership.Role.ADMIN)
    invitee = UserFactory(email='invitee@example.com')

    membership = services.accept_invitation(raw_token=raw_token, user=invitee)

    assert membership.organization == organization
    assert membership.role == Membership.Role.ADMIN


def test_reinviting_replaces_the_outstanding_invitation(owner_and_org):
    """Otherwise revoking one leaves another live token behind."""
    owner, organization = owner_and_org
    _first, first_token = _invite(organization, owner)
    _second, second_token = _invite(organization, owner)

    assert Invitation.objects.filter(accepted_at__isnull=True).count() == 1
    assert first_token != second_token

    invitee = UserFactory(email='invitee@example.com')
    with pytest.raises(services.OrganizationError):
        services.accept_invitation(raw_token=first_token, user=invitee)
    services.accept_invitation(raw_token=second_token, user=invitee)


def test_inviting_an_existing_member_is_refused(owner_and_org):
    owner, organization = owner_and_org

    with pytest.raises(services.OrganizationError):
        _invite(organization, owner, email=owner.email)
