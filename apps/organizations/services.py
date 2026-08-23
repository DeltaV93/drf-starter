"""Organization operations that have rules attached.

Kept out of the views so the rules hold wherever they are called from -- a
management command, the admin, a later API version.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit import AuditAction, audit
from utils.emails_utils import send_email
from utils.logging_utils import get_logger

from .models import (
    Invitation,
    Membership,
    Organization,
    generate_invitation_token,
    hash_invitation_token,
)

logger = get_logger(__name__)


class OrganizationError(Exception):
    """A rule was broken. The message is safe to show the caller."""


class SeatLimitReached(OrganizationError):
    pass


@transaction.atomic
def create_organization(*, name, owner):
    """Create an organization and make its creator the owner."""
    organization = Organization.objects.create(name=name)
    Membership.objects.create(
        organization=organization, user=owner, role=Membership.Role.OWNER
    )
    return organization


def seat_limit_for(organization):
    """Seats the organization's plan allows, or None when unlimited.

    Billing is optional, so this reaches for it defensively rather than
    importing at module level: with STRIPE_ENABLED off the app is not even
    installed, and organizations must still work.
    """
    if not settings.STRIPE_ENABLED:
        return None

    from apps.subscriptions.models import Subscription

    subscription = (
        Subscription.objects.select_related('plan')
        .filter(user__memberships__organization=organization, status='active')
        .first()
    )
    if subscription is None:
        return None
    return subscription.plan.user_limit


def assert_seat_available(organization):
    limit = seat_limit_for(organization)
    if limit is None:
        return
    if organization.seats_used >= limit:
        raise SeatLimitReached(
            f'This organization has used all {limit} seats on its plan. '
            'Remove a member or revoke a pending invitation first, or upgrade.'
        )


@transaction.atomic
def invite_member(*, organization, email, role, invited_by, accept_url_template):
    """Create (or replace) a pending invitation and email the raw token.

    Returns (invitation, raw_token). The raw token is never stored and never
    returned by any endpoint -- the email is the only place it exists.
    """
    email = email.strip().lower()

    if Membership.objects.filter(
        organization=organization, user__email__iexact=email
    ).exists():
        raise OrganizationError('That person is already a member of this organization.')

    assert_seat_available(organization)

    # Re-inviting replaces the outstanding invitation rather than adding a
    # second one, so revoking is unambiguous and the unique constraint holds.
    Invitation.objects.filter(
        organization=organization, email=email, accepted_at__isnull=True
    ).delete()

    raw_token = generate_invitation_token()
    invitation = Invitation.objects.create(
        organization=organization,
        email=email,
        role=role,
        token_hash=hash_invitation_token(raw_token),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=settings.INVITATION_EXPIRY_DAYS),
    )

    send_email(
        subject=f'You have been invited to join {organization.name}',
        template_name='emails/organization_invitation.html',
        context={
            'organization': organization,
            'invited_by': invited_by,
            'accept_url': accept_url_template.format(token=raw_token),
            'expiry_days': settings.INVITATION_EXPIRY_DAYS,
        },
        recipient_list=[email],
    )

    audit(
        AuditAction.MEMBER_INVITED,
        actor=invited_by,
        target=email,
        organization=organization.slug,
        role=role,
    )

    return invitation, raw_token


@transaction.atomic
def accept_invitation(*, raw_token, user):
    """Turn a valid invitation into a membership.

    The invitation is bound to the address it was sent to. Letting any
    authenticated holder of the token redeem it would mean a forwarded or
    leaked email grants access to whoever opens it first.
    """
    invitation = (
        Invitation.objects.select_for_update()
        .select_related('organization')
        .filter(token_hash=hash_invitation_token(raw_token))
        .first()
    )

    # One message for every failure: an attacker probing tokens learns nothing
    # about which ones exist, which are spent and which have expired.
    if invitation is None or not invitation.is_pending:
        raise OrganizationError('That invitation is not valid. Ask for a new one.')

    if invitation.email.lower() != (user.email or '').lower():
        raise OrganizationError('That invitation was sent to a different email address.')

    membership, created = Membership.objects.get_or_create(
        organization=invitation.organization,
        user=user,
        defaults={'role': invitation.role},
    )

    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=['accepted_at'])

    if created:
        logger.info('User joined organization %s', invitation.organization_id)
        audit(
            AuditAction.MEMBER_JOINED,
            actor=user,
            target=invitation.organization.slug,
            organization=invitation.organization.slug,
            role=membership.role,
        )

    return membership


@transaction.atomic
def change_role(*, membership, new_role):
    if membership.is_last_owner and new_role != Membership.Role.OWNER:
        raise OrganizationError('This is the only owner. Promote someone else to owner first.')
    previous_role = membership.role
    membership.role = new_role
    membership.save(update_fields=['role', 'updated_at'])
    audit(
        AuditAction.MEMBER_ROLE_CHANGED,
        target=str(membership.user),
        organization=membership.organization.slug,
        from_role=previous_role,
        to_role=new_role,
    )
    return membership


@transaction.atomic
def remove_member(*, membership):
    """Remove someone from an organization.

    An organization with no owner cannot be administered, billed or cancelled
    by anybody, and getting it back needs a database shell -- so the last one
    cannot be removed, and cannot leave.
    """
    if membership.is_last_owner:
        raise OrganizationError(
            'This is the only owner. Transfer ownership before removing them.'
        )
    audit(
        AuditAction.MEMBER_REMOVED,
        target=str(membership.user),
        organization=membership.organization.slug,
    )
    membership.delete()
