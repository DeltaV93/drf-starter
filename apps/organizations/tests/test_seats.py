"""Seat limits.

SubscriptionPlan.user_limit existed in the model from the start and was read
by nothing. This is what makes it mean something -- and it has to keep working
when billing is switched off, since the two flags are independent.
"""

import pytest
from django.conf import settings
from django.test import override_settings

from apps.organizations import services
from apps.organizations.models import Membership
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

# The billing app is not installed when STRIPE_ENABLED is off, so the cases
# that build a Subscription cannot even import their models.
needs_billing = pytest.mark.skipif(
    not settings.STRIPE_ENABLED, reason='billing is switched off'
)

ACCEPT_TEMPLATE = 'https://app.example.com/invitations/{token}'


def _invite(organization, inviter, email):
    return services.invite_member(
        organization=organization,
        email=email,
        role=Membership.Role.MEMBER,
        invited_by=inviter,
        accept_url_template=ACCEPT_TEMPLATE,
    )


@pytest.fixture
def org_on_a_two_seat_plan(owner_and_org):
    """An organization whose owner holds an active two-seat subscription."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.subscriptions.models import Subscription, SubscriptionPlan

    owner, organization = owner_and_org
    plan = SubscriptionPlan.objects.create(
        name='Team', stripe_price_id='price_team', user_limit=2, price=10
    )
    Subscription.objects.create(
        user=owner,
        plan=plan,
        stripe_subscription_id='sub_test_seats',
        status='active',
        current_period_end=timezone.now() + timedelta(days=30),
    )
    return owner, organization


@needs_billing
def test_the_plan_limit_counts_members_and_pending_invitations(org_on_a_two_seat_plan):
    """Pending invitations occupy a seat.

    Otherwise a two-seat plan can be walked past by sending five invitations
    and letting them all be accepted.
    """
    owner, organization = org_on_a_two_seat_plan

    _invite(organization, owner, 'second@example.com')  # 1 member + 1 pending = 2

    with pytest.raises(services.SeatLimitReached):
        _invite(organization, owner, 'third@example.com')


@needs_billing
def test_revoking_an_invitation_frees_the_seat(org_on_a_two_seat_plan):
    from apps.organizations.models import Invitation

    owner, organization = org_on_a_two_seat_plan
    _invite(organization, owner, 'second@example.com')
    Invitation.objects.filter(email='second@example.com').delete()

    # No longer over the limit, so this is allowed again.
    _invite(organization, owner, 'third@example.com')


@override_settings(STRIPE_ENABLED=False)
def test_seats_are_unlimited_when_billing_is_off(owner_and_org):
    """The two flags are independent: organizations work without billing."""
    owner, organization = owner_and_org

    for index in range(5):
        _invite(organization, owner, f'person{index}@example.com')

    assert organization.invitations.pending().count() == 5


def test_an_organization_with_no_subscription_is_unlimited(owner_and_org):
    """Free tiers exist. No plan means no limit to enforce."""
    owner, organization = owner_and_org

    assert services.seat_limit_for(organization) is None
    for index in range(3):
        _invite(organization, owner, f'free{index}@example.com')


@needs_billing
def test_accepted_members_count_against_the_limit(org_on_a_two_seat_plan):
    owner, organization = org_on_a_two_seat_plan
    _invitation, raw_token = _invite(organization, owner, 'second@example.com')
    services.accept_invitation(
        raw_token=raw_token, user=UserFactory(email='second@example.com')
    )

    assert organization.memberships.count() == 2
    with pytest.raises(services.SeatLimitReached):
        _invite(organization, owner, 'third@example.com')
