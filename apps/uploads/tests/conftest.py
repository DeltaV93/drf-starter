"""Uploads are opt-in; the app is not installed when the flag is off."""

import pytest
from django.conf import settings

from apps.authentication.backends import PASSWORD_BACKEND

collect_ignore_glob = [] if settings.UPLOADS_ENABLED else ['test_*.py']


@pytest.fixture(autouse=True)
def isolated_media(tmp_path, settings):
    """Keep uploaded bytes out of the repository."""
    settings.MEDIA_ROOT = tmp_path / 'media'
    return settings.MEDIA_ROOT


@pytest.fixture
def signed_in(client):
    from apps.users.factories import UserFactory

    def _sign_in(user=None):
        user = user or UserFactory()
        client.force_login(user, backend=PASSWORD_BACKEND)
        return client, user

    return _sign_in
