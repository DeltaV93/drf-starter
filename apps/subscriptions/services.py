"""Stripe integration.

Every Stripe call lives here so the views stay thin and the whole billing
surface can be mocked in one place during tests.
"""

from datetime import UTC, datetime

import stripe
from django.conf import settings

from utils.logging_utils import get_logger, log_exception, timed_function

from .models import Invoice, Payment, Subscription, UserAddOn

logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def _to_datetime(epoch_seconds):
    """Stripe returns UTC epoch seconds; Django wants an aware datetime."""
    return datetime.fromtimestamp(epoch_seconds, tz=UTC)


class StripeService:
    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def create_checkout_session(user, plan):
        """Start a hosted-checkout subscription flow. Returns the session id."""
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            # Wallets such as Apple Pay and Google Pay are surfaced through
            # the 'card' type; they are not separate payment method types.
            payment_method_types=['card'],
            line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            client_reference_id=str(user.pk),
        )
        logger.info('Created checkout session for user %s on plan %s', user.pk, plan.pk)
        return session.id

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def create_subscription(user, plan):
        """Create a Stripe subscription directly and mirror it locally."""
        customer = stripe.Customer.create(email=user.email, metadata={'user_id': str(user.pk)})
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': plan.stripe_price_id}],
        )

        subscription, _ = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'stripe_customer_id': customer.id,
                'stripe_subscription_id': stripe_subscription.id,
                'status': stripe_subscription.status,
                'current_period_end': _to_datetime(stripe_subscription.current_period_end),
            },
        )
        logger.info('Created subscription %s for user %s', subscription.pk, user.pk)
        return subscription

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def add_addon(user, add_on):
        """Attach an add-on price to the user's existing subscription."""
        subscription = Subscription.objects.get(user=user)
        item = stripe.SubscriptionItem.create(
            subscription=subscription.stripe_subscription_id,
            price=add_on.stripe_price_id,
        )
        user_addon, _ = UserAddOn.objects.get_or_create(
            user=user,
            add_on=add_on,
            defaults={'stripe_subscription_item_id': item.id},
        )
        logger.info('Added add-on %s for user %s', add_on.pk, user.pk)
        return user_addon

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def cancel_subscription(user, at_period_end=True):
        """Cancel the user's subscription, at period end by default."""
        subscription = Subscription.objects.get(user=user)
        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=at_period_end,
        )
        subscription.status = stripe_subscription.status
        subscription.save(update_fields=['status', 'updated_at'])
        logger.info('Cancelled subscription for user %s', user.pk)
        return subscription

    @staticmethod
    def process_webhook(payload, sig_header):
        """Verify and handle a Stripe webhook. Returns True if handled."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.exception('Malformed Stripe webhook payload')
            return False
        except stripe.error.SignatureVerificationError:
            logger.exception('Stripe webhook signature verification failed')
            return False

        handler = _WEBHOOK_HANDLERS.get(event['type'])
        if handler is None:
            logger.info('Ignoring unhandled Stripe event %s', event['type'])
            return True

        try:
            handler(event['data']['object'])
        except Exception:
            # Returning False makes Stripe retry, which is what we want for a
            # transient failure on our side.
            logger.exception('Failed to handle Stripe event %s', event['type'])
            return False

        logger.info('Handled Stripe event %s', event['type'])
        return True


# ---------------------------------------------------------------------------
# Webhook handlers
#
# Each takes the Stripe object from event['data']['object']. Keep them
# idempotent: Stripe retries, and the same event can arrive more than once.
# ---------------------------------------------------------------------------


def _handle_invoice_paid(invoice):
    user = _user_for_customer(invoice.get('customer'), invoice.get('customer_email'))
    if user is None:
        return

    Invoice.objects.update_or_create(
        stripe_invoice_id=invoice['id'],
        defaults={
            'user': user,
            'amount': (invoice.get('amount_paid') or 0) / 100,
            'status': invoice.get('status', 'paid'),
            'due_date': _to_datetime(invoice['due_date']) if invoice.get('due_date') else None,
            'pdf_url': invoice.get('invoice_pdf') or '',
        },
    )


def _handle_invoice_payment_failed(invoice):
    user = _user_for_customer(invoice.get('customer'), invoice.get('customer_email'))
    if user is None:
        return

    Invoice.objects.update_or_create(
        stripe_invoice_id=invoice['id'],
        defaults={
            'user': user,
            'amount': (invoice.get('amount_due') or 0) / 100,
            'status': invoice.get('status', 'payment_failed'),
            'due_date': _to_datetime(invoice['due_date']) if invoice.get('due_date') else None,
        },
    )
    Subscription.objects.filter(user=user).update(status=Subscription.Status.PAST_DUE)


def _handle_subscription_updated(stripe_subscription):
    subscription = Subscription.objects.filter(
        stripe_subscription_id=stripe_subscription['id']
    ).first()
    if subscription is None:
        logger.info(
            'No local subscription for Stripe id %s; ignoring.', stripe_subscription['id']
        )
        return

    subscription.status = stripe_subscription['status']
    if stripe_subscription.get('current_period_end'):
        subscription.current_period_end = _to_datetime(
            stripe_subscription['current_period_end']
        )
    subscription.save(update_fields=['status', 'current_period_end', 'updated_at'])


def _handle_subscription_deleted(stripe_subscription):
    Subscription.objects.filter(stripe_subscription_id=stripe_subscription['id']).update(
        status=Subscription.Status.CANCELED
    )


def _handle_payment_intent_succeeded(intent):
    user = _user_for_customer(intent.get('customer'), intent.get('receipt_email'))
    if user is None:
        return

    Payment.objects.update_or_create(
        stripe_payment_intent_id=intent['id'],
        defaults={
            'user': user,
            'amount': (intent.get('amount_received') or 0) / 100,
            'status': intent.get('status', 'succeeded'),
        },
    )


_WEBHOOK_HANDLERS = {
    'invoice.paid': _handle_invoice_paid,
    'invoice.payment_failed': _handle_invoice_payment_failed,
    'customer.subscription.updated': _handle_subscription_updated,
    'customer.subscription.deleted': _handle_subscription_deleted,
    'payment_intent.succeeded': _handle_payment_intent_succeeded,
}


def _user_for_customer(stripe_customer_id, email=None):
    """Resolve the local user for a Stripe customer, by id then by email."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if stripe_customer_id:
        subscription = (
            Subscription.objects.filter(stripe_customer_id=stripe_customer_id)
            .select_related('user')
            .first()
        )
        if subscription is not None:
            return subscription.user

    if email:
        return User.objects.filter(email__iexact=email).first()

    logger.warning('Could not resolve a user for Stripe customer %s', stripe_customer_id)
    return None
