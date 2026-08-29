"""The two documents that let the mobile app claim this site's own URLs.

The backend already emails links into the web app -- `/verify-email/<uid>/
<token>`, `/confirm-password/...`, `/invitations/<token>`. Publishing these
documents is what makes iOS and Android hand those *same* URLs to the
installed app instead of the browser. The alternative is emailing a custom
scheme (`drfstarter://...`), which is a dead link in every mail client on a
device that does not have the app, so it would mean two sets of emails and a
decision at send time about which client the recipient has.

Each document is derived entirely from settings, and each is published only
when its own half is configured. Neither is a secret: both are fetched
unauthenticated by Apple's and Google's infrastructure, and their contents are
public identifiers.

The paths themselves are fixed by the platforms and cannot carry the API's
`/api/v1/` prefix, which is why these mount at the project root -- the same
reason `apps/mcp_oauth` does.
"""

from django.conf import settings

APPLE_PATH = '.well-known/apple-app-site-association'
ANDROID_PATH = '.well-known/assetlinks.json'

# Handling links is one delegation; offering the site's saved passwords in the
# app's own login form is another. Both are wanted here: the app signs in
# against the same accounts as the website, so a password manager that cannot
# see across the two makes people type what they already have stored.
ANDROID_RELATIONS = [
    'delegate_permission/common.handle_all_urls',
    'delegate_permission/common.get_login_creds',
]


def ios_configured():
    return bool(settings.MOBILE_IOS_APP_ID)


def android_configured():
    return bool(
        settings.MOBILE_ANDROID_PACKAGE and settings.MOBILE_ANDROID_SHA256_FINGERPRINTS
    )


def apple_app_site_association():
    """The `applinks` document iOS fetches when the app is installed.

    Written in the `appIDs`/`components` form rather than the older
    `appID`/`paths` one. Both still work; this is the form Apple documents,
    and it is the one that can express exclusions later without a rewrite.

    `webcredentials` is the second half and is easy to leave out: it is what
    lets iOS offer a password saved for the website when someone signs in to
    the app. Without it a shared account looks like two accounts to the
    keychain.
    """
    app_id = settings.MOBILE_IOS_APP_ID
    return {
        'applinks': {
            'details': [
                {
                    'appIDs': [app_id],
                    'components': [{'/': path} for path in settings.MOBILE_DEEP_LINK_PATHS],
                }
            ]
        },
        'webcredentials': {'apps': [app_id]},
    }


def asset_links():
    """The Digital Asset Links document Android fetches to verify App Links.

    A JSON array at the top level, which the platform requires -- so this is
    one of the two endpoints in the project that does not answer with the
    `{status, message, data, errors}` envelope.

    More than one fingerprint is normal rather than exceptional: with Play App
    Signing the upload key and the distribution key differ, and a build
    installed from a debug APK differs again. Listing only the release
    fingerprint is why links work in production and silently fall back to the
    browser on a developer's own device.
    """
    return [
        {
            'relation': list(ANDROID_RELATIONS),
            'target': {
                'namespace': 'android_app',
                'package_name': settings.MOBILE_ANDROID_PACKAGE,
                'sha256_cert_fingerprints': list(settings.MOBILE_ANDROID_SHA256_FINGERPRINTS),
            },
        }
    ]
