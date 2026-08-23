"""Stripe webhook handling.

The webhook is the one endpoint that is CSRF-exempt and unauthenticated, so
its signature check is the only thing standing between Stripe's callbacks and
anyone on the internet. These tests pin that down.
"""

from unittest.mock import patch

import pytest
import stripe
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

WEBHOOK_URL_NAME = 'v1:stripe_webhook'


@pytest.fixture
def webhook_client():
    # CSRF enforcement on: the webhook must work without a token, and this is
    # what proves the csrf_exempt decorator is still in place.
    return APIClient(enforce_csrf_checks=True)


def _post(client, payload=b'{}', signature='t=1,v1=abc'):
    kwargs = {'content_type': 'application/json'}
    if signature is not None:
        kwargs['HTTP_STRIPE_SIGNATURE'] = signature
    return client.post(reverse(WEBHOOK_URL_NAME), payload, **kwargs)


def test_webhook_rejects_a_request_with_no_signature(webhook_client):
    response = _post(webhook_client, signature=None)

    assert response.status_code == 400


def test_webhook_rejects_a_bad_signature(webhook_client):
    with patch('stripe.Webhook.construct_event') as construct:
        construct.side_effect = stripe.error.SignatureVerificationError('bad', 'sig')
        response = _post(webhook_client)

    assert response.status_code == 400


def test_webhook_rejects_a_malformed_payload(webhook_client):
    with patch('stripe.Webhook.construct_event') as construct:
        construct.side_effect = ValueError('not json')
        response = _post(webhook_client)

    assert response.status_code == 400


def test_webhook_accepts_a_signed_event_without_a_csrf_token(webhook_client):
    with patch('stripe.Webhook.construct_event') as construct:
        construct.return_value = {'type': 'ping', 'data': {'object': {}}}
        response = _post(webhook_client)

    assert response.status_code == 200


def test_subscription_updated_syncs_status_and_period(webhook_client, active_subscription):
    event = {
        'type': 'customer.subscription.updated',
        'data': {
            'object': {
                'id': active_subscription.stripe_subscription_id,
                'status': 'past_due',
                'current_period_end': 1893456000,
            }
        },
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        response = _post(webhook_client)

    assert response.status_code == 200
    active_subscription.refresh_from_db()
    assert active_subscription.status == 'past_due'


def test_subscription_deleted_marks_it_canceled(webhook_client, active_subscription):
    event = {
        'type': 'customer.subscription.deleted',
        'data': {'object': {'id': active_subscription.stripe_subscription_id}},
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        _post(webhook_client)

    active_subscription.refresh_from_db()
    assert active_subscription.status == 'canceled'


def test_invoice_paid_records_an_invoice(webhook_client, user, active_subscription):
    from apps.subscriptions.models import Invoice

    event = {
        'type': 'invoice.paid',
        'data': {
            'object': {
                'id': 'in_123',
                'customer': 'cus_123',
                'amount_paid': 1999,
                'status': 'paid',
                'invoice_pdf': 'https://stripe.example/in_123.pdf',
            }
        },
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        _post(webhook_client)

    invoice = Invoice.objects.get(stripe_invoice_id='in_123')
    assert invoice.user == user
    assert str(invoice.amount) == '19.99'


def test_replaying_the_same_invoice_event_is_idempotent(
    webhook_client, user, active_subscription
):
    from apps.subscriptions.models import Invoice

    event = {
        'type': 'invoice.paid',
        'data': {
            'object': {
                'id': 'in_123',
                'customer': 'cus_123',
                'amount_paid': 1999,
                'status': 'paid',
            }
        },
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        _post(webhook_client)
        _post(webhook_client)

    assert Invoice.objects.filter(stripe_invoice_id='in_123').count() == 1


def test_payment_failed_moves_the_subscription_to_past_due(
    webhook_client, user, active_subscription
):
    event = {
        'type': 'invoice.payment_failed',
        'data': {
            'object': {
                'id': 'in_456',
                'customer': 'cus_123',
                'amount_due': 1999,
                'status': 'open',
            }
        },
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        _post(webhook_client)

    active_subscription.refresh_from_db()
    assert active_subscription.status == 'past_due'


def test_an_unhandled_event_type_is_acknowledged(webhook_client):
    event = {'type': 'customer.created', 'data': {'object': {'id': 'cus_999'}}}

    with patch('stripe.Webhook.construct_event', return_value=event):
        response = _post(webhook_client)

    # Acknowledged, so Stripe stops retrying an event we deliberately ignore.
    assert response.status_code == 200


def test_a_handler_failure_asks_stripe_to_retry(webhook_client, active_subscription):
    event = {
        'type': 'customer.subscription.updated',
        'data': {
            'object': {
                'id': active_subscription.stripe_subscription_id,
                'status': 'active',
                'current_period_end': 1893456000,
            }
        },
    }

    def explode(_obj):
        raise RuntimeError('boom')

    # The registry holds a direct reference to the handler, so patching the
    # module attribute would not be seen -- the dict entry is what dispatches.
    with (
        patch('stripe.Webhook.construct_event', return_value=event),
        patch.dict(
            'apps.subscriptions.services._WEBHOOK_HANDLERS',
            {'customer.subscription.updated': explode},
        ),
    ):
        response = _post(webhook_client)

    # A non-2xx makes Stripe retry, which is what we want for a failure on
    # our side rather than a bad event.
    assert response.status_code == 400


def test_a_well_formed_event_is_not_treated_as_a_failure(webhook_client, active_subscription):
    """Guards the test above: without the injected failure this must pass."""
    event = {
        'type': 'customer.subscription.updated',
        'data': {
            'object': {
                'id': active_subscription.stripe_subscription_id,
                'status': 'active',
                'current_period_end': 1893456000,
            }
        },
    }

    with patch('stripe.Webhook.construct_event', return_value=event):
        response = _post(webhook_client)

    assert response.status_code == 200
