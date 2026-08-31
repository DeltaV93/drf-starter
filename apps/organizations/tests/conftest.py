"""Fixtures for the organization tests.

The app is opt-in. base.py reads ORGANIZATIONS_ENABLED while it is imported,
which decides INSTALLED_APPS and the URLconf, so it cannot be toggled after
the fact -- testing.py turns it on for the suite. When CI runs the flag
combinations with it off the app is not installed at all, so these modules
must not even be collected.
"""

import pytest
from django.conf import settings

from apps.authentication.backends import PASSWORD_BACKEND

collect_ignore_glob = [] if settings.ORGANIZATIONS_ENABLED else ['test_*.py']


@pytest.fixture
def owner_and_org(db):
    from apps.organizations.services import create_organization
    from apps.users.factories import UserFactory

    user = UserFactory()
    organization = create_organization(name='Acme', owner=user)
    return user, organization


@pytest.fixture
def sign_in(client):
    """Establish a session without going through the login endpoint."""

    def _sign_in(user):
        client.force_login(user, backend=PASSWORD_BACKEND)
        return client

    return _sign_in
