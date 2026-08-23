"""Rate limiting on the credential and email-sending endpoints.

SimpleRateThrottle reads THROTTLE_RATES onto the class at import time, so
override_settings does not reach it -- the rate is patched on the class
instead.
"""

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.core.throttles import LoginRateThrottle, PasswordResetRateThrottle

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_history():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def tight_login_limit(monkeypatch):
    monkeypatch.setitem(LoginRateThrottle.THROTTLE_RATES, 'login', '2/min')


@pytest.fixture
def tight_reset_limit(monkeypatch):
    monkeypatch.setitem(PasswordResetRateThrottle.THROTTLE_RATES, 'password_reset', '2/hour')


def test_repeated_failed_logins_are_throttled(api_client, user, tight_login_limit):
    credentials = {'username': user.username, 'password': 'not-the-password'}

    first = api_client.post(reverse('v1:login'), credentials)
    second = api_client.post(reverse('v1:login'), credentials)
    third = api_client.post(reverse('v1:login'), credentials)

    assert first.status_code == 400
    assert second.status_code == 400
    assert third.status_code == 429


def test_password_reset_requests_are_throttled(api_client, user, tight_reset_limit):
    payload = {'email': user.email}

    api_client.post(reverse('v1:password_reset_request'), payload)
    api_client.post(reverse('v1:password_reset_request'), payload)
    third = api_client.post(reverse('v1:password_reset_request'), payload)

    assert third.status_code == 429


def test_the_health_endpoint_is_never_throttled(api_client, tight_login_limit):
    for _ in range(5):
        response = api_client.get(reverse('v1:health'))
        assert response.status_code == 200
