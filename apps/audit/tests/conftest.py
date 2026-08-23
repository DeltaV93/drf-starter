"""The audit app is opt-in; not installed when the flag is off."""

import pytest
from django.conf import settings

collect_ignore_glob = [] if settings.AUDIT_LOG_ENABLED else ['test_*.py']


@pytest.fixture
def signed_in(client):
    from apps.users.factories import UserFactory

    def _sign_in(user=None):
        user = user or UserFactory()
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        return client, user

    return _sign_in
