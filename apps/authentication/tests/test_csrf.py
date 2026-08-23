"""The session-auth CSRF contract.

DRF marks every APIView csrf_exempt at the middleware level and instead
enforces CSRF inside SessionAuthentication, for session-authenticated
requests only. These tests pin that behaviour down, because it is the part
of session auth that silently breaks when settings drift.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged_in_client(user):
    client = APIClient(enforce_csrf_checks=True)
    client.post(reverse('v1:login'), {'username': user.username, 'password': DEFAULT_PASSWORD})
    return client


def test_csrf_endpoint_issues_a_token_and_a_cookie(api_client):
    response = api_client.get(reverse('v1:csrf_token'))

    assert response.status_code == 200
    assert response.data['data']['csrfToken']
    assert 'csrftoken' in response.cookies


def test_an_authenticated_write_without_the_header_is_rejected(logged_in_client):
    response = logged_in_client.patch(reverse('v1:user_me'), {'first_name': 'Nope'})

    assert response.status_code == 403


def test_an_authenticated_write_with_the_header_succeeds(logged_in_client, user):
    csrf_token = logged_in_client.cookies['csrftoken'].value

    response = logged_in_client.patch(
        reverse('v1:user_me'), {'first_name': 'Yes'}, HTTP_X_CSRFTOKEN=csrf_token
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'Yes'


def test_a_stale_csrf_token_is_rejected(logged_in_client):
    response = logged_in_client.patch(
        reverse('v1:user_me'),
        {'first_name': 'Nope'},
        HTTP_X_CSRFTOKEN='a-token-from-somewhere-else',
    )

    assert response.status_code == 403


def test_reads_do_not_need_a_csrf_token(logged_in_client):
    response = logged_in_client.get(reverse('v1:user_me'))

    assert response.status_code == 200
