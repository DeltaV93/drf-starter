from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from apps.subscriptions.models import Subscription, UserAddOn
from apps.subscriptions.services import StripeService

pytestmark = pytest.mark.django_db


class _StripeObject(dict):
    """Stripe's objects are dicts that also support attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


PERIOD_END = 1893456000  # 2030-01-01T00:00:00Z


def test_create_checkout_session_returns_the_session_id(user, plan):
    with patch('stripe.checkout.Session.create') as create:
        create.return_value = _StripeObject(id='cs_test_123')

        session_id = StripeService.create_checkout_session(user, plan)

    assert session_id == 'cs_test_123'
    kwargs = create.call_args.kwargs
    assert kwargs['line_items'] == [{'price': plan.stripe_price_id, 'quantity': 1}]
    assert kwargs['mode'] == 'subscription'
    # Wallets ride on 'card'; naming them separately is rejected by Stripe.
    assert kwargs['payment_method_types'] == ['card']


def test_create_subscription_mirrors_stripe_locally(user, plan):
    with (
        patch('stripe.Customer.create') as customer_create,
        patch('stripe.Subscription.create') as subscription_create,
    ):
        customer_create.return_value = _StripeObject(id='cus_123')
        subscription_create.return_value = _StripeObject(
            id='sub_123', status='active', current_period_end=PERIOD_END
        )

        subscription = StripeService.create_subscription(user, plan)

    assert subscription.stripe_subscription_id == 'sub_123'
    assert subscription.stripe_customer_id == 'cus_123'
    assert subscription.status == 'active'
    assert subscription.plan == plan
    assert subscription.current_period_end == datetime(2030, 1, 1, tzinfo=UTC)


def test_create_subscription_is_idempotent_for_a_user(user, plan):
    with (
        patch('stripe.Customer.create') as customer_create,
        patch('stripe.Subscription.create') as subscription_create,
    ):
        customer_create.return_value = _StripeObject(id='cus_123')
        subscription_create.return_value = _StripeObject(
            id='sub_123', status='active', current_period_end=PERIOD_END
        )

        StripeService.create_subscription(user, plan)
        StripeService.create_subscription(user, plan)

    assert Subscription.objects.filter(user=user).count() == 1


def test_add_addon_records_the_subscription_item(user, plan, add_on):
    Subscription.objects.create(
        user=user,
        plan=plan,
        stripe_subscription_id='sub_123',
        status='active',
        current_period_end=datetime(2030, 1, 1, tzinfo=UTC),
    )

    with patch('stripe.SubscriptionItem.create') as item_create:
        item_create.return_value = _StripeObject(id='si_123')

        user_addon = StripeService.add_addon(user, add_on)

    assert user_addon.stripe_subscription_item_id == 'si_123'
    assert UserAddOn.objects.filter(user=user, add_on=add_on).count() == 1


def test_cancel_subscription_records_the_new_status(user, plan):
    Subscription.objects.create(
        user=user,
        plan=plan,
        stripe_subscription_id='sub_123',
        status='active',
        current_period_end=datetime(2030, 1, 1, tzinfo=UTC),
    )

    with patch('stripe.Subscription.modify') as modify:
        modify.return_value = _StripeObject(id='sub_123', status='canceled')

        subscription = StripeService.cancel_subscription(user)

    assert subscription.status == 'canceled'
    assert modify.call_args.kwargs['cancel_at_period_end'] is True
