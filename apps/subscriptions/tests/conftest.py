from datetime import UTC

import pytest
from django.conf import settings

# Billing is an optional module. When STRIPE_ENABLED is false the app is not
# in INSTALLED_APPS at all, so its models cannot even be imported -- skip the
# whole directory rather than failing collection.
collect_ignore_glob = [] if settings.STRIPE_ENABLED else ['test_*.py']


@pytest.fixture
def plan(db):
    from apps.subscriptions.models import SubscriptionPlan

    return SubscriptionPlan.objects.create(
        name='Pro', stripe_price_id='price_pro', user_limit=10, price='19.99'
    )


@pytest.fixture
def add_on(db):
    from apps.subscriptions.models import AddOn

    return AddOn.objects.create(
        name='Extra seats', stripe_price_id='price_seats', price='5.00'
    )


@pytest.fixture
def active_subscription(db, user, plan):
    from datetime import datetime

    from apps.subscriptions.models import Subscription

    return Subscription.objects.create(
        user=user,
        plan=plan,
        stripe_customer_id='cus_123',
        stripe_subscription_id='sub_123',
        status='active',
        current_period_end=datetime(2030, 1, 1, tzinfo=UTC),
    )
