"""The gate that can lock every user out of the app.

Worth being careful with. The failure that matters is not "the block did not
fire" -- it is the block firing when it should not have, which turns a
configuration slip into an outage nobody can clear from the client side.
"""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.app_releases.models import AppRelease, Requirement
from apps.app_releases.versions import is_at_least, parse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    """The view caches per platform, so a row written by one test would
    otherwise still be answered for the next one."""
    cache.clear()
    yield
    cache.clear()


def check(client, version='1.0.0', platform='ios'):
    return client.get(
        reverse('v1:app_upgrade_check'), {'platform': platform, 'version': version}
    )


# ---------------------------------------------------------------------------
# The default: nothing configured
# ---------------------------------------------------------------------------


def test_an_empty_table_gates_nobody(api_client):
    """A fresh deployment must never block anyone. This is the whole reason
    the floors default to empty rather than to the current version."""
    response = check(api_client, version='0.0.1')

    assert response.status_code == 200
    assert response.data['data']['requirement'] == Requirement.NONE


def test_the_check_needs_no_credential(api_client):
    """A build old enough to be blocked may be one whose sign-in is broken.

    Requiring authentication would mean the only users who could learn they
    must upgrade are the ones who did not need telling.
    """
    assert 'Authorization' not in api_client._credentials
    assert check(api_client).status_code == 200


def test_the_check_needs_no_csrf_token(api_client):
    """`api_client` enforces CSRF; a GET from a token client has no cookie."""
    assert check(api_client).status_code == 200


# ---------------------------------------------------------------------------
# Blocking and nudging
# ---------------------------------------------------------------------------


def test_a_build_below_the_minimum_is_required_to_upgrade(api_client):
    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')

    assert check(api_client, '1.9.9').data['data']['requirement'] == Requirement.REQUIRED


def test_a_build_at_the_minimum_is_allowed(api_client):
    """Off-by-one here locks out the exact version you just shipped."""
    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')

    assert check(api_client, '2.0.0').data['data']['requirement'] == Requirement.NONE


def test_a_build_below_only_the_recommendation_is_nudged_not_blocked(api_client):
    AppRelease.objects.create(
        platform='ios', minimum_version='1.0.0', recommended_version='2.0.0'
    )

    assert check(api_client, '1.5.0').data['data']['requirement'] == Requirement.RECOMMENDED


def test_the_minimum_wins_over_the_recommendation(api_client):
    AppRelease.objects.create(
        platform='ios', minimum_version='2.0.0', recommended_version='3.0.0'
    )

    assert check(api_client, '1.0.0').data['data']['requirement'] == Requirement.REQUIRED


def test_platforms_are_gated_independently(api_client):
    """App Review can hold an iOS build for days after the Android one ships.
    Gating both on one number would block the platform that is not at fault."""
    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')

    assert (
        check(api_client, '1.0.0', 'ios').data['data']['requirement'] == Requirement.REQUIRED
    )
    assert (
        check(api_client, '1.0.0', 'android').data['data']['requirement'] == Requirement.NONE
    )


def test_the_store_url_and_message_reach_the_client(api_client):
    AppRelease.objects.create(
        platform='android',
        minimum_version='2.0.0',
        store_url='https://play.google.com/store/apps/details?id=com.example',
        message='Version 1 could lose drafts. Please update.',
    )

    data = check(api_client, '1.0.0', 'android').data['data']

    assert data['store_url'].startswith('https://play.google.com/')
    assert data['message'] == 'Version 1 could lose drafts. Please update.'


# ---------------------------------------------------------------------------
# Refusing to answer
# ---------------------------------------------------------------------------


def test_an_unknown_platform_is_rejected_rather_than_guessed(api_client):
    response = check(api_client, platform='windows-phone')

    assert response.status_code == 400


def test_a_missing_version_is_rejected(api_client):
    response = api_client.get(reverse('v1:app_upgrade_check'), {'platform': 'ios'})

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Comparing versions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'version,minimum,expected',
    [
        ('1.0.0', '1.0.0', True),
        ('1.0.1', '1.0.0', True),
        ('1.1.0', '1.0.9', True),
        ('2.0.0', '10.0.0', False),
        # Not a string comparison: '10' sorts before '9' as text.
        ('10.0.0', '9.0.0', True),
        ('1.10.0', '1.9.0', True),
        # Missing components are zero, so a two-part version satisfies a
        # three-part floor of the same number.
        ('1.2', '1.2.0', True),
        ('1.2', '1.2.1', False),
        ('1.2.0.4', '1.2.0', True),
    ],
)
def test_versions_compare_numerically(version, minimum, expected):
    assert is_at_least(version, minimum) is expected


@pytest.mark.parametrize('value', ['1.2.3-hotfix', '1.2.3+build7', '2.0 (beta)'])
def test_a_suffix_after_the_numbers_is_ignored(value):
    assert parse(value) is not None
    assert is_at_least(value, '1.0.0')


def test_an_empty_version_is_rejected_rather_than_read_as_unknown(api_client):
    """Distinct from the case below: sending no version at all is a client
    bug, and answering it with 'carry on' would hide that. The client treats
    any non-200 as carry on anyway, so saying 400 costs nothing and is true."""
    assert check(api_client, '').status_code == 400


@pytest.mark.parametrize('value', ['unknown', 'v1.2.3', 'nightly'])
def test_a_version_that_cannot_be_read_is_never_blocked(api_client, value):
    """Fail open, and deliberately.

    A client sending something unparseable is far more likely to be a newer
    build with a versioning scheme this code has not met than an ancient one.
    Blocking on "I do not understand you" would turn a format change into a
    lockout, and there is no way back from that without a store release.
    """
    AppRelease.objects.create(platform='ios', minimum_version='99.0.0')

    assert check(api_client, value).data['data']['requirement'] == Requirement.NONE


# ---------------------------------------------------------------------------
# Guarding the admin against contradictory rows
# ---------------------------------------------------------------------------


def test_a_recommendation_below_the_minimum_is_refused():
    """Nobody could ever see it: everyone below it is already blocked."""
    release = AppRelease(platform='ios', minimum_version='2.0.0', recommended_version='1.0.0')

    with pytest.raises(ValidationError) as caught:
        release.full_clean()

    assert 'recommended_version' in caught.value.error_dict


def test_a_version_that_is_not_a_version_is_refused_at_the_admin():
    """The comparator fails open, so a typo here would silently gate nobody.
    Catching it at entry is the only place it can still be a visible error."""
    release = AppRelease(platform='ios', minimum_version='latest')

    with pytest.raises(ValidationError) as caught:
        release.full_clean()

    assert 'minimum_version' in caught.value.error_dict


def test_one_row_per_platform():
    AppRelease.objects.create(platform='ios', minimum_version='1.0.0')

    with pytest.raises(ValidationError):
        AppRelease(platform='ios', minimum_version='2.0.0').full_clean()


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


def test_repeated_checks_do_not_hit_the_database_every_time(
    api_client, django_assert_num_queries
):
    """Every installation calls this on launch and on foreground.

    Unqueried it would be one row read per app open, forever, for an answer
    that changes a handful of times in a product's life.
    """
    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')

    with django_assert_num_queries(1):
        check(api_client, '1.0.0')
    with django_assert_num_queries(0):
        check(api_client, '1.0.0')
        check(api_client, '3.0.0')


def test_the_cache_is_kept_per_platform(api_client):
    """One key for both would let an iOS floor answer an Android question."""
    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')

    assert (
        check(api_client, '1.0.0', 'ios').data['data']['requirement'] == Requirement.REQUIRED
    )
    assert (
        check(api_client, '1.0.0', 'android').data['data']['requirement'] == Requirement.NONE
    )


def test_what_is_cached_survives_a_model_change(api_client):
    """Fields, not a pickled row.

    A cached `AppRelease` instance that outlives a migration adding or
    removing a field comes back unreadable, which surfaces as a 500 on a
    public endpoint minutes after an ordinary deploy.
    """
    from django.core.cache import cache as django_cache

    AppRelease.objects.create(platform='ios', minimum_version='2.0.0')
    check(api_client, '1.0.0')

    assert django_cache.get('app_release:ios') == {
        'minimum_version': '2.0.0',
        'recommended_version': '',
        'store_url': '',
        'message': '',
    }
