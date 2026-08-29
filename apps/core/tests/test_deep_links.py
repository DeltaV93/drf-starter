"""The association documents, and the two ways they silently fail.

Both are fetched by someone else's infrastructure, on a schedule nobody
controls, and the result of getting one wrong is not an error -- it is links
quietly opening the browser instead of the app, forever, with a 200 on every
request. So the things worth pinning are the ones with no other symptom: the
exact paths, the absence of the API envelope, and the fact that an
unconfigured deployment 404s rather than publishing an empty document.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.core import deep_links

APPLE_URL = '/.well-known/apple-app-site-association'
ANDROID_URL = '/.well-known/assetlinks.json'

IOS = {'MOBILE_IOS_APP_ID': 'ABCDE12345.com.example.app'}
ANDROID = {
    'MOBILE_ANDROID_PACKAGE': 'com.example.app',
    'MOBILE_ANDROID_SHA256_FINGERPRINTS': ['AA:BB:CC', 'DD:EE:FF'],
}


# ---------------------------------------------------------------------------
# Where they live
# ---------------------------------------------------------------------------


def test_the_paths_are_the_ones_the_platforms_fetch():
    """Neither path is negotiable, and neither can carry the /api/v1/ prefix.

    Apple in particular fetches this exact URL with no extension -- naming the
    file `.json` is the single most common way to publish a document that is
    never read.
    """
    assert reverse('apple-app-site-association') == APPLE_URL
    assert reverse('android-asset-links') == ANDROID_URL


# ---------------------------------------------------------------------------
# Unconfigured
# ---------------------------------------------------------------------------


@override_settings(MOBILE_IOS_APP_ID='')
def test_apple_404s_when_no_ios_app_is_configured(client):
    """404, not an empty document.

    An `applinks` document with no matching detail tells iOS the association
    was checked and refused, and that answer is cached -- so publishing one by
    accident is worse than publishing nothing.
    """
    assert client.get(APPLE_URL).status_code == 404


@override_settings(MOBILE_ANDROID_PACKAGE='', MOBILE_ANDROID_SHA256_FINGERPRINTS=[])
def test_android_404s_when_no_android_app_is_configured(client):
    assert client.get(ANDROID_URL).status_code == 404


@override_settings(
    MOBILE_ANDROID_PACKAGE='com.example.app', MOBILE_ANDROID_SHA256_FINGERPRINTS=[]
)
def test_android_404s_when_the_package_has_no_fingerprint(client):
    """A target with no fingerprint verifies nothing, and Android rejects the
    whole document rather than ignoring the bad entry."""
    assert client.get(ANDROID_URL).status_code == 404


# ---------------------------------------------------------------------------
# Configured
# ---------------------------------------------------------------------------


@override_settings(**IOS)
def test_apple_publishes_the_app_id_against_the_claimed_paths(client):
    response = client.get(APPLE_URL)

    assert response.status_code == 200
    detail = response.json()['applinks']['details'][0]
    assert detail['appIDs'] == [IOS['MOBILE_IOS_APP_ID']]
    assert {c['/'] for c in detail['components']} == set(
        deep_links.settings.MOBILE_DEEP_LINK_PATHS
    )


@override_settings(**IOS)
def test_apple_also_shares_saved_passwords_with_the_app(client):
    """`webcredentials` is the half that is easy to leave out.

    Without it, iOS treats the site and the app as two different places and
    will not offer a password saved for one when signing in to the other --
    even though they are the same account.
    """
    assert client.get(APPLE_URL).json()['webcredentials']['apps'] == [IOS['MOBILE_IOS_APP_ID']]


@override_settings(**IOS)
def test_the_apple_document_is_not_wrapped_in_the_api_envelope(client):
    """Every other endpoint answers `{status, message, data, errors}`. This
    one cannot: the operating system parses it, and it is looking for
    `applinks` at the top level."""
    payload = client.get(APPLE_URL).json()

    assert 'applinks' in payload
    assert 'data' not in payload
    assert 'status' not in payload


@override_settings(**ANDROID)
def test_android_publishes_every_fingerprint(client):
    """More than one is normal rather than exceptional -- Play App Signing and
    the upload key differ, and a debug build differs again. Listing only the
    release fingerprint is why links work in production and fall back to the
    browser on a developer's own handset."""
    response = client.get(ANDROID_URL)

    assert response.status_code == 200
    target = response.json()[0]['target']
    assert target['package_name'] == ANDROID['MOBILE_ANDROID_PACKAGE']
    assert target['sha256_cert_fingerprints'] == ANDROID['MOBILE_ANDROID_SHA256_FINGERPRINTS']


@override_settings(**ANDROID)
def test_android_delegates_both_links_and_saved_passwords(client):
    relations = client.get(ANDROID_URL).json()[0]['relation']

    assert 'delegate_permission/common.handle_all_urls' in relations
    assert 'delegate_permission/common.get_login_creds' in relations


@override_settings(**ANDROID)
def test_the_android_document_is_a_bare_array(client):
    """Google's format is an array at the top level. Wrapping it in the API
    envelope -- or in any object -- makes it unparseable."""
    assert isinstance(client.get(ANDROID_URL).json(), list)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------


@override_settings(**IOS)
def test_the_document_is_readable_without_any_credential(client):
    """Apple's crawler has no session, no token and no CSRF cookie. Leaving
    the default authentication classes in place would run CSRF enforcement on
    a document whose entire purpose is to be fetched anonymously."""
    assert client.get(APPLE_URL).status_code == 200


@pytest.mark.django_db
@override_settings(**IOS)
def test_the_spa_catch_all_does_not_swallow_it(client):
    """`.well-known/` is already excluded from the SPA catch-all. If that ever
    changed, this path would answer 200 with index.html -- which parses as
    neither JSON nor an error, and looks fine in every dashboard."""
    response = client.get(APPLE_URL)

    assert response['Content-Type'].startswith('application/json')
