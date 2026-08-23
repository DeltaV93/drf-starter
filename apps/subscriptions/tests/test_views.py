from unittest.mock import patch

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_plans_are_public(api_client, plan):
    response = api_client.get(reverse('v1:plan_list'))

    assert response.status_code == 200
    assert [p['stripe_price_id'] for p in response.data['data']] == ['price_pro']


def test_inactive_plans_are_hidden(api_client, plan):
    plan.is_active = False
    plan.save(update_fields=['is_active'])

    response = api_client.get(reverse('v1:plan_list'))

    assert response.data['data'] == []


def test_subscribe_returns_a_checkout_session(auth_client, plan):
    url = reverse('v1:subscribe', kwargs={'stripe_price_id': plan.stripe_price_id})

    with patch('apps.subscriptions.services.StripeService.create_checkout_session') as create:
        create.return_value = 'cs_test_123'
        response = auth_client.post(url)

    assert response.status_code == 200
    assert response.data['data']['checkout_session_id'] == 'cs_test_123'


def test_subscribe_404s_for_an_unknown_plan(auth_client):
    url = reverse('v1:subscribe', kwargs={'stripe_price_id': 'price_nope'})

    response = auth_client.post(url)

    assert response.status_code == 404


def test_subscribe_requires_authentication(api_client, plan):
    url = reverse('v1:subscribe', kwargs={'stripe_price_id': plan.stripe_price_id})

    response = api_client.post(url)

    assert response.status_code in (401, 403)


def test_my_subscription_returns_null_without_one(auth_client):
    response = auth_client.get(reverse('v1:my_subscription'))

    assert response.status_code == 200
    assert response.data.get('data') is None


def test_my_subscription_returns_the_current_one(auth_client, active_subscription):
    response = auth_client.get(reverse('v1:my_subscription'))

    assert response.data['data']['status'] == 'active'
    assert response.data['data']['is_current'] is True


def test_add_addon_requires_a_subscription(auth_client, add_on):
    url = reverse('v1:add_addon', kwargs={'addon_id': add_on.pk})

    response = auth_client.post(url)

    assert response.status_code == 400


def test_add_addon_succeeds_with_a_subscription(auth_client, add_on, active_subscription):
    url = reverse('v1:add_addon', kwargs={'addon_id': add_on.pk})

    with patch('apps.subscriptions.services.StripeService.add_addon') as add:
        response = auth_client.post(url)

    assert response.status_code == 200
    add.assert_called_once()


def test_add_addon_404s_for_an_unknown_addon(auth_client, active_subscription):
    url = reverse('v1:add_addon', kwargs={'addon_id': 9999})

    response = auth_client.post(url)

    assert response.status_code == 404


def test_cancel_404s_without_a_subscription(auth_client):
    response = auth_client.post(reverse('v1:cancel_subscription'))

    assert response.status_code == 404


def test_cancel_succeeds_with_a_subscription(auth_client, active_subscription):
    with patch('apps.subscriptions.services.StripeService.cancel_subscription') as cancel:
        cancel.return_value = active_subscription
        response = auth_client.post(reverse('v1:cancel_subscription'))

    assert response.status_code == 200
    cancel.assert_called_once()
