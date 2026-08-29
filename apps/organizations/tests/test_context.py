"""Which organization a request acts for, for each kind of client.

The browser's answer lives in its session. A bearer-token client has no
session at all, so without the header below it would be permanently pinned to
whichever organization happens to sort first -- switching would appear to work
(the endpoint returns 200) and then have no effect on the next request. That
is the failure these tests exist for: it is invisible until someone with two
organizations notices they are looking at the wrong one.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.organizations.context import HEADER_NAME
from apps.organizations.services import create_organization
from apps.users.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def member_of_two():
    """A user who belongs to two organizations, oldest first."""
    user = UserFactory()
    first = create_organization(name='First Org', owner=user)
    second = create_organization(name='Second Org', owner=user)
    return user, first, second


def token_client(user):
    """A client authenticated the way the mobile app is: header, no cookies."""
    client = APIClient()
    response = client.post(
        reverse('v1:token_obtain'),
        {'username': user.username, 'password': DEFAULT_PASSWORD},
    )
    access = response.data['data']['access']
    return APIClient(HTTP_AUTHORIZATION=f'Bearer {access}')


def active_slug(client, **extra):
    response = client.get(reverse('v1:organization_active'), **extra)
    assert response.status_code == 200
    organization = response.data['data']['organization']
    return organization['slug'] if organization else None


# ---------------------------------------------------------------------------
# The default
# ---------------------------------------------------------------------------


def test_a_client_that_names_nothing_gets_its_earliest_organization(member_of_two):
    """So a user with exactly one organization never has to choose it."""
    user, first, _second = member_of_two

    assert active_slug(token_client(user)) == first.slug


# ---------------------------------------------------------------------------
# The header
# ---------------------------------------------------------------------------


def test_the_header_selects_the_organization(member_of_two):
    user, _first, second = member_of_two

    client = token_client(user)

    assert active_slug(client, **{'HTTP_X_ORGANIZATION': second.slug}) == second.slug


def test_the_header_is_checked_against_the_caller_s_own_memberships(member_of_two):
    """The reason a header is safe here.

    Naming somebody else's organization cannot select it -- resolution is
    filtered by membership, exactly as the session path is. The worst an
    attacker who controls this header achieves is acting as an organization
    the user already belongs to.
    """
    user, first, _second = member_of_two
    stranger_org = create_organization(name='Not Yours', owner=UserFactory())

    client = token_client(user)

    assert active_slug(client, **{'HTTP_X_ORGANIZATION': stranger_org.slug}) == first.slug


def test_a_stale_header_falls_back_rather_than_erroring(member_of_two):
    """A device left signed in keeps sending the slug it last knew. If that
    organization is gone, the app should keep working rather than 400 on every
    request until someone reinstalls it."""
    user, first, _second = member_of_two

    client = token_client(user)

    assert active_slug(client, **{'HTTP_X_ORGANIZATION': 'deleted-org'}) == first.slug


def test_the_header_name_is_allowed_through_cors():
    """A browser drops a disallowed header at preflight without telling the
    page, so this is the one way the setting can be wrong and look right."""
    from django.conf import settings

    assert HEADER_NAME.lower() in settings.CORS_ALLOW_HEADERS


# ---------------------------------------------------------------------------
# The session, unchanged
# ---------------------------------------------------------------------------


def test_switching_still_sticks_for_a_session_client(member_of_two, sign_in):
    """The website's behaviour, which the header must not have disturbed."""
    user, _first, second = member_of_two
    client = sign_in(user)

    switched = client.post(reverse('v1:organization_switch', args=[second.slug]))
    assert switched.status_code == 200

    response = client.get(reverse('v1:organization_active'))
    assert response.json()['data']['organization']['slug'] == second.slug


def test_the_header_wins_over_a_session_choice(member_of_two, sign_in):
    """Both present is not a normal shape, but it has to resolve one way and
    the per-request instruction is the more recent one."""
    user, first, second = member_of_two
    client = sign_in(user)
    client.post(reverse('v1:organization_switch', args=[second.slug]))

    response = client.get(
        reverse('v1:organization_active'), **{'HTTP_X_ORGANIZATION': first.slug}
    )

    assert response.json()['data']['organization']['slug'] == first.slug


def test_switching_does_not_crash_a_client_with_no_session(member_of_two):
    """`set_active_organization` writes to the session. A token client has
    none, so the write has to be skipped rather than raising -- the response
    is what tells the app which slug to send from then on."""
    user, _first, second = member_of_two

    response = token_client(user).post(reverse('v1:organization_switch', args=[second.slug]))

    assert response.status_code == 200
    assert response.data['data']['slug'] == second.slug
