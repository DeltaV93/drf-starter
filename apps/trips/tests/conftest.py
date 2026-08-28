import pytest
from django.utils import timezone
from apps.users.models import CustomUser
from apps.trips.models import Trip, TripHome


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username='testuser@example.com',
        email='testuser@example.com',
        password='testpass123',
    )


@pytest.fixture
def trip(user):
    return Trip.objects.create(
        user=user,
        name='Test Trip',
        start_address='123 Main St, San Francisco, CA',
        end_address='456 Oak Ave, San Francisco, CA',
    )


@pytest.fixture
def trip_with_homes(trip):
    now = timezone.now()
    for i in range(3):
        TripHome.objects.create(
            trip=trip,
            address=f'{100 + i} Test St, San Francisco, CA',
            start_time=now.replace(hour=10 + i),
            end_time=now.replace(hour=11 + i),
            visit_order=i + 1,
            lat=37.7749 + (i * 0.001),
            lng=-122.4194 + (i * 0.001),
            zpid=f'zpid{i}',
            price=500000 + (i * 100000),
            bedrooms=3 + i,
            bathrooms=2.0,
            sqft=2000,
        )
    return trip
