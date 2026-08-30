"""Registering a device, and the two ways a registry leaks.

A push registry looks trivial until you notice that the operating system
reissues tokens whenever it likes and that people sign in on borrowed phones.
Both of those turn a stale row into somebody else's notifications arriving on
a screen they do not own, which is what most of this file is about.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.push.models import Device
from apps.users.factories import UserFactory

# Collection is skipped with the flag off -- see conftest.py, which has to do
# it there rather than here because importing this module imports the model.
pytestmark = pytest.mark.django_db

TOKEN = 'ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]'


def register(client, token=TOKEN, **extra):
    payload = {'token': token, 'platform': 'ios', 'device_name': 'Test iPhone', **extra}
    return client.post(reverse('v1:push_device_list'), payload)


def test_registering_stores_the_device(auth_client, user):
    response = register(auth_client)

    assert response.status_code == 201
    device = Device.objects.get(token=TOKEN)
    assert device.user == user
    assert device.platform == 'ios'


def test_registering_twice_updates_rather_than_duplicating(auth_client):
    """The client re-sends its token on every launch, because it has no way to
    know whether the token is new. The endpoint has to absorb that."""
    register(auth_client)
    second = register(auth_client, device_name='Renamed iPhone')

    assert second.status_code == 200
    assert Device.objects.filter(token=TOKEN).count() == 1
    assert Device.objects.get(token=TOKEN).device_name == 'Renamed iPhone'


def test_a_token_moves_to_whoever_registers_it_last(auth_client, user):
    """The leak this prevents.

    Signing in on a colleague's phone and then signing out must not leave that
    phone receiving your notifications. The token identifies the installation,
    so it can only ever belong to the account currently using it.
    """
    register(auth_client)

    other = UserFactory()
    other_client = APIClient()
    other_client.force_authenticate(user=other)
    register(other_client)

    assert Device.objects.filter(token=TOKEN).count() == 1
    assert Device.objects.get(token=TOKEN).user == other


def test_registering_revives_a_token_the_push_service_had_reported_as_gone(auth_client):
    register(auth_client)
    Device.objects.filter(token=TOKEN).update(is_active=False)

    register(auth_client)

    assert Device.objects.get(token=TOKEN).is_active is True


def test_an_unknown_platform_is_refused(auth_client):
    response = register(auth_client, platform='pager')

    assert response.status_code == 400
    assert not Device.objects.exists()


def test_registration_requires_a_signed_in_user(api_client):
    assert register(api_client).status_code == 401


# ---------------------------------------------------------------------------
# Listing and unregistering
# ---------------------------------------------------------------------------


def test_listing_shows_only_your_own_devices(auth_client):
    register(auth_client)

    other_client = APIClient()
    other_client.force_authenticate(user=UserFactory())
    register(other_client, token='ExponentPushToken[someone-else]')

    response = auth_client.get(reverse('v1:push_device_list'))

    assert response.status_code == 200
    assert [d['token'] for d in response.data['data']] == [TOKEN]


def test_unregistering_removes_the_device(auth_client):
    register(auth_client)

    response = auth_client.delete(reverse('v1:push_device_detail', args=[TOKEN]))

    assert response.status_code == 200
    assert not Device.objects.filter(token=TOKEN).exists()


def test_you_cannot_unregister_somebody_else_s_device(auth_client):
    """Without the user filter, knowing any token would be enough to
    unsubscribe another person's phone."""
    other_client = APIClient()
    other_client.force_authenticate(user=UserFactory())
    register(other_client)

    response = auth_client.delete(reverse('v1:push_device_detail', args=[TOKEN]))

    assert response.status_code == 404
    assert Device.objects.filter(token=TOKEN).exists()


def test_an_expo_style_token_survives_the_round_trip_through_the_url(auth_client):
    """The brackets are the point. A `slug` converter would not match this
    token, and every unregister would 404 with nothing to explain it."""
    register(auth_client)

    response = auth_client.delete(reverse('v1:push_device_detail', args=[TOKEN]))

    assert response.status_code == 200
