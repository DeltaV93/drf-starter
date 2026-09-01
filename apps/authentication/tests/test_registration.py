import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'first_name': 'New',
        'last_name': 'User',
        'password': 'sufficiently-long-passphrase-9',
        'password2': 'sufficiently-long-passphrase-9',
    }
    payload.update(overrides)
    return payload


def test_register_creates_user_and_sends_verification_email(api_client):
    response = api_client.post(reverse('v1:register'), _payload())

    assert response.status_code == 201
    user = User.objects.get(username='newuser')
    assert user.check_password('sufficiently-long-passphrase-9')
    assert user.email_verified is False
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_register_returns_a_csrf_token_for_the_new_session(api_client):
    response = api_client.post(reverse('v1:register'), _payload())

    assert response.data['data']['csrfToken']


def test_register_rejects_mismatched_passwords(api_client):
    response = api_client.post(
        reverse('v1:register'), _payload(password2='something-else-entirely')
    )

    assert response.status_code == 400
    assert 'password2' in response.data['errors']
    assert not User.objects.filter(username='newuser').exists()


def test_register_rejects_a_weak_password(api_client):
    response = api_client.post(
        reverse('v1:register'), _payload(password='pass', password2='pass')
    )

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_register_rejects_a_password_similar_to_the_username(api_client):
    # Django's UserAttributeSimilarityValidator only fires when the serializer
    # passes the unsaved user through to validate_password.
    response = api_client.post(
        reverse('v1:register'),
        _payload(username='alexanderson', password='alexanderson', password2='alexanderson'),
    )

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_register_stores_the_address_lowercased(api_client):
    response = api_client.post(reverse('v1:register'), _payload(email='Ada@Example.COM'))

    assert response.status_code == 201
    assert User.objects.get(email='ada@example.com')
    # And the response echoes what was stored, not what was sent.
    assert response.data['data']['user']['email'] == 'ada@example.com'


def test_an_account_registered_in_one_case_signs_in_in_another(api_client):
    api_client.post(reverse('v1:register'), _payload(email='Ada@Example.COM'))

    response = APIClient().post(
        reverse('v1:login'),
        {'identifier': 'ADA@example.com', 'password': 'sufficiently-long-passphrase-9'},
    )

    assert response.status_code == 200


def test_register_rejects_a_duplicate_email_regardless_of_case(api_client):
    UserFactory(email='taken@example.com')

    response = api_client.post(reverse('v1:register'), _payload(email='TAKEN@example.com'))

    assert response.status_code == 400
    assert 'email' in response.data['errors']


def test_register_rejects_a_duplicate_username(api_client):
    UserFactory(username='newuser')

    response = api_client.post(reverse('v1:register'), _payload())

    assert response.status_code == 400
    assert 'username' in response.data['errors']


# --------------------------------------------------------------------------
# The username is optional
# --------------------------------------------------------------------------


@pytest.mark.parametrize('username', ['', None])
def test_register_accepts_an_empty_username(api_client, username):
    response = api_client.post(
        reverse('v1:register'), _payload(username=username), format='json'
    )

    assert response.status_code == 201, response.data
    user = User.objects.get(email='newuser@example.com')
    # NULL, not '': the column is unique, so a second account registering
    # without a handle would collide with the first.
    assert user.username is None


def test_register_omitting_the_username_entirely(api_client):
    payload = _payload()
    del payload['username']

    response = api_client.post(reverse('v1:register'), payload)

    assert response.status_code == 201, response.data
    assert User.objects.get(email='newuser@example.com').username is None


def test_two_accounts_can_both_register_without_a_username(api_client):
    """The case a unique NOT NULL column would have made impossible."""
    first = _payload()
    del first['username']
    second = {**first, 'email': 'second@example.com'}

    assert api_client.post(reverse('v1:register'), first).status_code == 201
    # A second client: registration signs the first one in, and its session
    # then carries a CSRF token the next POST would have to echo.
    assert APIClient().post(reverse('v1:register'), second).status_code == 201

    assert User.objects.filter(username__isnull=True).count() == 2


def test_register_rejects_a_duplicate_username_regardless_of_case(api_client):
    UserFactory(username='NewUser')

    response = api_client.post(reverse('v1:register'), _payload())

    assert response.status_code == 400
    assert 'username' in response.data['errors']


def test_register_rejects_a_username_shaped_like_an_email(api_client):
    """Sign-in resolves addresses first, so such a handle is unusable --
    and could be somebody else's address."""
    response = api_client.post(
        reverse('v1:register'), _payload(username='someone@example.com')
    )

    assert response.status_code == 400
    assert 'username' in response.data['errors']


@override_settings(
    # Two real Django backends rather than a social one, so the failure under
    # test is precisely "Django will not guess between backends" and not a
    # social_core configuration error that happens to raise nearby.
    AUTHENTICATION_BACKENDS=[
        'apps.authentication.backends.EmailOrUsernameBackend',
        'django.contrib.auth.backends.AllowAllUsersModelBackend',
    ]
)
def test_registration_works_with_more_than_one_authentication_backend(client):
    """SOCIAL_AUTH_ENABLED used to 500 every signup.

    The new user has not been through authenticate(), so there is no `backend`
    attribute for login() to infer from, and with more than one entry in
    AUTHENTICATION_BACKENDS Django refuses to guess. The view names the
    password backend explicitly.
    """
    response = client.post(reverse('v1:register'), _payload(), content_type='application/json')

    assert response.status_code == 201, response.content
    assert User.objects.filter(email='newuser@example.com').exists()
    # And the session really was established, not merely not-crashed.
    assert '_auth_user_id' in client.session
