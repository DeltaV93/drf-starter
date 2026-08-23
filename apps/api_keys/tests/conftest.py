"""API keys are opt-in; the app is not installed when the flag is off."""

import pytest
from django.conf import settings

collect_ignore_glob = [] if settings.API_KEYS_ENABLED else ['test_*.py']


@pytest.fixture
def make_key(db):
    """Create a key and hand back (APIKey, raw_key)."""
    from apps.api_keys.models import APIKey, generate_key
    from apps.users.factories import UserFactory

    def _make(user=None, **kwargs):
        full_key, prefix, hashed_secret = generate_key()
        key = APIKey.objects.create(
            user=user or UserFactory(),
            name=kwargs.pop('name', 'CI'),
            prefix=prefix,
            hashed_secret=hashed_secret,
            **kwargs,
        )
        return key, full_key

    return _make
