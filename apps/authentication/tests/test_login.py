import pytest
from django.urls import reverse

from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_login_succeeds_with_valid_credentials(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert response.data['message'] == 'Login successful.'
    assert response.data['data']['user']['username'] == user.username
    assert '_auth_user_id' in api_client.session


def test_login_returns_the_rotated_csrf_token(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )

    assert response.data['data']['csrfToken']


def test_login_rejects_a_wrong_password(api_client, user):
    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': 'not-the-password'}
    )

    assert response.status_code == 400
    assert '_auth_user_id' not in api_client.session


def test_login_does_not_reveal_whether_the_account_exists(api_client, user):
    missing = api_client.post(
        reverse('v1:login'), {'identifier': 'nobody', 'password': 'not-the-password'}
    )
    wrong_password = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': 'not-the-password'}
    )

    assert missing.status_code == wrong_password.status_code == 400
    assert missing.data['errors'] == wrong_password.data['errors']


def test_login_rejects_an_inactive_user(api_client):
    user = UserFactory(is_active=False)

    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 400


def test_login_requires_both_fields(api_client):
    response = api_client.post(reverse('v1:login'), {'identifier': 'someone'})

    assert response.status_code == 400
    assert 'password' in response.data['errors']


def test_logout_clears_the_session(api_client, user):
    api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )
    csrf_token = api_client.cookies['csrftoken'].value

    response = api_client.post(reverse('v1:logout'), HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 200
    assert '_auth_user_id' not in api_client.session


def test_logout_requires_authentication(api_client):
    response = api_client.post(reverse('v1:logout'))

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------
# The identifier: email always, username only if the account has one
# --------------------------------------------------------------------------


def test_an_account_with_no_username_signs_in_with_its_email(api_client):
    user = UserFactory(username=None)

    response = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert response.data['data']['user']['username'] is None


def test_an_account_with_a_username_can_sign_in_with_either(api_client):
    user = UserFactory(username='ada')

    by_username = api_client.post(
        reverse('v1:login'), {'identifier': 'ada', 'password': DEFAULT_PASSWORD}
    )
    assert by_username.status_code == 200

    api_client.post(
        reverse('v1:logout'), HTTP_X_CSRFTOKEN=api_client.cookies['csrftoken'].value
    )

    by_email = api_client.post(
        reverse('v1:login'), {'identifier': user.email, 'password': DEFAULT_PASSWORD}
    )
    assert by_email.status_code == 200


def test_the_email_is_matched_regardless_of_case(api_client):
    """Rows created before signups lowercased, or by the admin, or imported."""
    UserFactory(email='Ada@Example.com')

    response = api_client.post(
        reverse('v1:login'), {'identifier': 'ada@example.com', 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200


def test_the_username_is_matched_regardless_of_case(api_client):
    UserFactory(username='Ada')

    response = api_client.post(
        reverse('v1:login'), {'identifier': 'ADA', 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200


def test_an_email_wins_over_someone_elses_username(api_client):
    """Deterministic when the two namespaces collide.

    Registration refuses to create this collision, but the admin and an
    imported row can still produce it, and it must not be the deciding factor
    in whose account a password is checked against.
    """
    owner = UserFactory(email='ada@example.com')
    UserFactory(username='ada@example.com')

    response = api_client.post(
        reverse('v1:login'), {'identifier': 'ada@example.com', 'password': DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert response.data['data']['user']['id'] == owner.pk


@pytest.mark.parametrize('field', ['username', 'email'])
@pytest.mark.parametrize('fmt', ['json', 'multipart'])
def test_a_client_that_posts_the_old_field_names_is_understood(api_client, user, field, fmt):
    """A mobile build already in the app stores cannot be updated in place.

    Both encodings, because a form-encoded body arrives as a QueryDict and the
    aliasing has to survive being copied out of one.
    """
    response = api_client.post(
        reverse('v1:login'), {field: user.email, 'password': DEFAULT_PASSWORD}, format=fmt
    )

    assert response.status_code == 200


def test_login_requires_an_identifier(api_client):
    response = api_client.post(reverse('v1:login'), {'password': DEFAULT_PASSWORD})

    assert response.status_code == 400
    assert 'identifier' in response.data['errors']
