"""SubscriptionMiddleware annotation.

The original implementation compared current_period_end against
`now + grace_period`, which flagged every healthy subscription renewing
within the grace window as expired. These tests pin the corrected meaning:
a current subscription is never expired, and a lapsed one expires only after
the grace period has run out.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def session_client(user):
    """A client with a real session.

    Middleware runs before DRF authentication, so it sees Django's
    request.user -- which force_authenticate never sets. Only a session
    login exercises the middleware.
    """
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def subscription_factory(db, user, plan):
    from apps.subscriptions.models import Subscription

    def make(status, period_end):
        return Subscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id=f'sub_{status}_{period_end.timestamp()}',
            status=status,
            current_period_end=period_end,
        )

    return make


def _expired_for(client, url_name='v1:user_me'):
    """Run a request through the middleware and report what it annotated."""
    response = client.get(reverse(url_name))
    return response.wsgi_request.subscription_expired


def test_no_subscription_counts_as_expired(session_client):
    assert _expired_for(session_client) is True


def test_an_active_subscription_renewing_soon_is_not_expired(
    session_client, subscription_factory
):
    # The old logic called this expired, because the period ends inside the
    # grace window. It is the normal state of a healthy monthly plan.
    subscription_factory('active', timezone.now() + timedelta(days=3))

    assert _expired_for(session_client) is False


def test_a_trialing_subscription_is_not_expired(session_client, subscription_factory):
    subscription_factory('trialing', timezone.now() + timedelta(days=3))

    assert _expired_for(session_client) is False


def test_a_lapsed_subscription_inside_the_grace_period_is_not_expired(
    session_client, subscription_factory, settings
):
    settings.SUBSCRIPTION_GRACE_PERIOD_DAYS = 14
    subscription_factory('past_due', timezone.now() - timedelta(days=3))

    assert _expired_for(session_client) is False


def test_a_lapsed_subscription_past_the_grace_period_is_expired(
    session_client, subscription_factory, settings
):
    settings.SUBSCRIPTION_GRACE_PERIOD_DAYS = 14
    subscription_factory('past_due', timezone.now() - timedelta(days=20))

    assert _expired_for(session_client) is True


def test_the_middleware_attaches_the_subscription_itself(session_client, subscription_factory):
    subscription = subscription_factory('active', timezone.now() + timedelta(days=30))

    response = session_client.get(reverse('v1:user_me'))

    assert response.wsgi_request.subscription == subscription


def test_anonymous_requests_are_annotated_without_a_database_lookup(api_client):
    # Not the health endpoint: HealthCheckMiddleware short-circuits that one
    # before SubscriptionMiddleware runs, by design.
    response = api_client.get(reverse('v1:csrf_token'))

    assert response.wsgi_request.subscription is None
    assert response.wsgi_request.subscription_expired is False
