import pytest
from django.test import Client
from django.urls import reverse
from apps.trips.models import Trip, TripHome


@pytest.mark.django_db
class TestTripsListView:
    def test_list_trips_authenticated(self, user, trip):
        client = Client()
        client.force_login(user)
        response = client.get('/api/v1/trips/')
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == trip.name

    def test_list_trips_unauthenticated(self):
        client = Client()
        response = client.get('/api/v1/trips/')
        assert response.status_code == 401

    def test_create_trip(self, user):
        client = Client()
        client.force_login(user)
        payload = {
            'name': 'New Trip',
            'start_address': '123 Main St, San Francisco, CA',
            'end_address': '456 Oak Ave, San Francisco, CA',
            'homes': [
                {
                    'address': '789 Pine St, San Francisco, CA',
                    'start_time': '2025-08-28T10:00:00Z',
                    'end_time': '2025-08-28T11:00:00Z',
                    'lat': 37.7749,
                    'lng': -122.4194,
                }
            ],
        }
        response = client.post('/api/v1/trips/', data=payload, content_type='application/json')
        assert response.status_code == 201
        data = response.json()
        assert data['data']['name'] == 'New Trip'
        assert len(data['data']['homes']) == 1


@pytest.mark.django_db
class TestTripDetailView:
    def test_get_trip(self, user, trip_with_homes):
        client = Client()
        client.force_login(user)
        response = client.get(f'/api/v1/trips/{trip_with_homes.id}/')
        assert response.status_code == 200
        data = response.json()
        assert data['data']['id'] == trip_with_homes.id
        assert len(data['data']['homes']) == 3

    def test_update_trip(self, user, trip_with_homes):
        client = Client()
        client.force_login(user)
        payload = {'name': 'Updated Trip Name'}
        response = client.put(
            f'/api/v1/trips/{trip_with_homes.id}/',
            data=payload,
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['data']['name'] == 'Updated Trip Name'

    def test_delete_trip(self, user, trip):
        client = Client()
        client.force_login(user)
        response = client.delete(f'/api/v1/trips/{trip.id}/')
        assert response.status_code == 204
        assert not Trip.objects.filter(id=trip.id).exists()
