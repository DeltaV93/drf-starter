"""Data export: what goes in it, and what must never.

An export is a file the user receives by email and may forward, store or lose.
A credential in it is a credential leak with extra steps.
"""

import json

import pytest
from django.urls import reverse

from apps.users.factories import UserFactory
from utils import gdpr_export
from utils.gdpr_tasks import export_json_for, make_download_token, read_download_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def signed_in(client):
    def _sign_in(user=None):
        user = user or UserFactory()
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        return client, user

    return _sign_in


# --------------------------------------------------------------------------
# What it contains
# --------------------------------------------------------------------------


def test_the_export_contains_the_profile():
    user = UserFactory(first_name='Ada', last_name='Lovelace')

    payload = gdpr_export.build_export(user)

    profile = payload['sections']['profile']
    assert profile['email'] == user.email
    assert profile['first_name'] == 'Ada'


def test_the_password_hash_is_never_exported():
    """The one thing that must not be in a file the user can forward."""
    user = UserFactory()

    text = export_json_for(user)

    assert user.password not in text
    assert 'password' not in json.loads(text)['sections']['profile']


@pytest.mark.parametrize(
    'credential_key',
    ['password', 'hashed_secret', 'hashed_code', 'encrypted_secret', 'token_hash', 'secret'],
)
def test_a_credential_key_is_stripped_at_any_depth(credential_key):
    """Belt and braces: a collector that grows a field cannot leak one."""
    nested = {'a': [{'b': {credential_key: 'leaked', 'keep': 'kept'}}]}

    scrubbed = gdpr_export.scrub(nested)

    assert 'leaked' not in json.dumps(scrubbed)
    assert scrubbed['a'][0]['b']['keep'] == 'kept'


def test_a_failing_collector_does_not_lose_the_rest(monkeypatch):
    """A partial export the user can act on beats a 500 they cannot."""

    def explode(user):
        raise RuntimeError('collector is broken')

    monkeypatch.setitem(gdpr_export._COLLECTORS, 'broken', explode)
    user = UserFactory()

    payload = gdpr_export.build_export(user)

    assert 'error' in payload['sections']['broken']
    assert payload['sections']['profile']['email'] == user.email


def test_the_export_is_json_serialisable():
    """Dates and Decimals appear throughout; json.dumps must not choke."""
    user = UserFactory()

    text = export_json_for(user)

    assert json.loads(text)['user_id'] == user.pk


def test_only_installed_features_contribute_sections():
    """A collector for a switched-off app would import a missing model."""
    from django.conf import settings

    names = set(gdpr_export.collectors())

    assert 'profile' in names
    assert ('organizations' in names) == settings.ORGANIZATIONS_ENABLED
    assert ('api_keys' in names) == settings.API_KEYS_ENABLED
    assert ('files' in names) == settings.UPLOADS_ENABLED


def test_api_keys_are_listed_without_their_secrets():
    from django.conf import settings

    if not settings.API_KEYS_ENABLED:
        pytest.skip('API keys are switched off')

    from apps.api_keys.models import APIKey, generate_key

    user = UserFactory()
    full_key, prefix, hashed_secret = generate_key()
    APIKey.objects.create(user=user, name='CI', prefix=prefix, hashed_secret=hashed_secret)

    text = export_json_for(user)

    assert prefix in text  # identifies the key
    assert full_key not in text  # but not the credential
    assert hashed_secret not in text


# --------------------------------------------------------------------------
# The link
# --------------------------------------------------------------------------


def test_a_token_names_its_own_user():
    user = UserFactory()

    assert read_download_token(make_download_token(user)) == str(user.pk)


def test_a_tampered_token_is_refused():
    user = UserFactory()
    token = make_download_token(user)

    assert read_download_token(token[:-1] + 'x') is None
    assert read_download_token('not-a-token') is None


def test_an_expired_token_is_refused(settings):
    user = UserFactory()
    token = make_download_token(user)

    settings.GDPR_EXPORT_LINK_TIMEOUT = -1

    assert read_download_token(token) is None


def test_a_token_cannot_be_replayed_against_another_signer():
    """Namespaced by salt, so a signature from elsewhere in the project is not
    accepted here."""
    from django.core.signing import TimestampSigner

    user = UserFactory()
    foreign = TimestampSigner(salt='something-else').sign(str(user.pk))

    assert read_download_token(foreign) is None


# --------------------------------------------------------------------------
# The endpoints
# --------------------------------------------------------------------------


def test_requesting_an_export_sends_a_link_by_email(signed_in):
    from django.core import mail

    client, user = signed_in()

    response = client.post(reverse('v1:data_export_request'))

    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    # Delivered to the account's own address, not to whoever holds the session.
    assert 'account/export/' in mail.outbox[0].body


def test_the_response_does_not_carry_the_data_or_the_link(signed_in):
    client, _user = signed_in()

    response = client.post(reverse('v1:data_export_request'))

    body = response.content.decode()
    assert 'account/export/' not in body


def test_anonymous_callers_cannot_request_an_export(client):
    assert client.post(reverse('v1:data_export_request')).status_code in (401, 403)


def test_downloading_with_a_valid_token_returns_the_file(client):
    user = UserFactory()
    token = make_download_token(user)

    response = client.get(reverse('v1:data_export_download', args=[token]))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    assert 'attachment' in response['Content-Disposition']
    # Personal data behind a URL that will sit in a mail client's history.
    assert 'no-store' in response['Cache-Control']
    assert json.loads(response.content)['user_id'] == user.pk


def test_downloading_with_a_bad_token_is_refused(client):
    response = client.get(reverse('v1:data_export_download', args=['nonsense']))

    assert response.status_code == 400


def test_a_token_for_a_deactivated_account_stops_working(client):
    user = UserFactory()
    token = make_download_token(user)

    user.is_active = False
    user.save(update_fields=['is_active'])

    assert client.get(reverse('v1:data_export_download', args=[token])).status_code == 400
