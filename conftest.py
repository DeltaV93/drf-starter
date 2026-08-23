"""Fixtures shared by the whole suite."""

import pytest
from rest_framework.test import APIClient

from apps.users.factories import DEFAULT_PASSWORD, UserFactory


@pytest.fixture
def api_client():
    """Unauthenticated client with CSRF checks enforced.

    DRF's test client skips CSRF by default, which would let a regression in
    the CSRF configuration pass unnoticed. `enforce_csrf_checks` keeps the
    session-auth contract honest.
    """
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


@pytest.fixture
def auth_client(user):
    """Client authenticated as `user`, with CSRF enforcement relaxed.

    Use this for tests about a view's own behaviour. The CSRF contract itself
    is covered separately in apps/authentication/tests/test_csrf.py.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client
