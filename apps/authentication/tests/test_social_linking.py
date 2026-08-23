"""The account-linking rule, which is the security question in social login.

python-social-auth ships `associate_by_email` in its default pipeline: a social
identity is handed the existing account with the same address. That is an
account-takeover path -- anyone who can make a provider assert an address
inherits the password account. This pipeline refuses instead.
"""

import pytest
from django.conf import settings
from django.urls import reverse

from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

if not settings.SOCIAL_AUTH_ENABLED:  # pragma: no cover - the flag-off CI run
    pytest.skip('social login is switched off', allow_module_level=True)

from apps.authentication.social_pipeline import (  # noqa: E402
    EmailAlreadyRegistered,
    refuse_silent_takeover,
)


def _run(details, user=None):
    return refuse_silent_takeover(strategy=None, details=details, backend=object(), user=user)


def test_an_unknown_email_passes_through():
    assert _run({'email': 'brand-new@example.com'}) is None


def test_an_email_belonging_to_someone_else_is_refused():
    """The takeover path. A provider asserting an address must not be enough."""
    existing = UserFactory(email='victim@example.com')

    with pytest.raises(EmailAlreadyRegistered):
        _run({'email': 'victim@example.com'})

    existing.refresh_from_db()
    assert existing.email == 'victim@example.com'


def test_the_match_is_case_insensitive():
    """Otherwise VICTIM@example.com walks straight past the check."""
    UserFactory(email='victim@example.com')

    with pytest.raises(EmailAlreadyRegistered):
        _run({'email': 'VICTIM@Example.COM'})


def test_surrounding_whitespace_does_not_defeat_the_check():
    UserFactory(email='victim@example.com')

    with pytest.raises(EmailAlreadyRegistered):
        _run({'email': '  victim@example.com  '})


def test_an_already_linked_identity_is_left_alone():
    """`user` set means social_core matched the provider's stable id, which is
    the association we do trust."""
    existing = UserFactory(email='linked@example.com')

    assert _run({'email': 'linked@example.com'}, user=existing) is None


def test_a_provider_that_returns_no_email_is_not_blocked():
    assert _run({}) is None
    assert _run({'email': ''}) is None


def test_the_refusal_tells_the_user_what_to_do():
    UserFactory(email='victim@example.com')

    with pytest.raises(EmailAlreadyRegistered) as exc:
        _run({'email': 'victim@example.com'})

    message = str(exc.value)
    assert 'password' in message.lower()
    assert 'link' in message.lower()


def test_associate_by_email_is_not_in_the_pipeline():
    """The default pipeline's step is what this replaces; if it comes back,
    everything above is bypassed."""
    assert not any('associate_by_email' in step for step in settings.SOCIAL_AUTH_PIPELINE)
    assert any('refuse_silent_takeover' in step for step in settings.SOCIAL_AUTH_PIPELINE)


def test_the_guard_runs_before_the_user_is_created():
    """After create_user it would be too late -- the account would exist."""
    steps = list(settings.SOCIAL_AUTH_PIPELINE)
    guard = next(i for i, s in enumerate(steps) if 'refuse_silent_takeover' in s)
    create = next(i for i, s in enumerate(steps) if s.endswith('user.create_user'))

    assert guard < create


# --------------------------------------------------------------------------
# Trusting the provider's email
# --------------------------------------------------------------------------


def test_an_address_is_only_marked_verified_when_the_provider_says_so():
    from apps.authentication.social_pipeline import mark_email_verified

    user = UserFactory(email_verified=False)

    # No signal at all -- the common case for providers that report nothing.
    mark_email_verified(strategy=None, details={'email': user.email}, user=user, response={})
    user.refresh_from_db()
    assert user.email_verified is False

    # An explicit false is still false.
    mark_email_verified(
        strategy=None,
        details={'email': user.email},
        user=user,
        response={'email_verified': False},
    )
    user.refresh_from_db()
    assert user.email_verified is False


def test_a_verified_address_from_the_provider_is_accepted():
    from apps.authentication.social_pipeline import mark_email_verified

    user = UserFactory(email_verified=False)

    mark_email_verified(
        strategy=None,
        details={'email': user.email},
        user=user,
        response={'email_verified': True},
    )

    user.refresh_from_db()
    assert user.email_verified is True


# --------------------------------------------------------------------------
# Unlinking
# --------------------------------------------------------------------------


def test_unlinking_the_only_credential_is_refused(client):
    """Without a usable password, the last provider is the only way in, and
    password reset cannot help -- there is nothing to reset to."""
    from social_django.models import UserSocialAuth

    user = UserFactory()
    user.set_unusable_password()
    user.save(update_fields=['password'])
    UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='123')
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.post(reverse('v1:social_disconnect', args=['google-oauth2']))

    assert response.status_code == 400
    assert UserSocialAuth.objects.filter(user=user).exists()


def test_unlinking_is_allowed_when_a_password_remains(client):
    from social_django.models import UserSocialAuth

    user = UserFactory()  # has a usable password
    UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='123')
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.post(reverse('v1:social_disconnect', args=['google-oauth2']))

    assert response.status_code == 200
    assert not UserSocialAuth.objects.filter(user=user).exists()


def test_unlinking_is_allowed_when_another_provider_remains(client):
    from social_django.models import UserSocialAuth

    user = UserFactory()
    user.set_unusable_password()
    user.save(update_fields=['password'])
    UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='1')
    UserSocialAuth.objects.create(user=user, provider='linkedin-oauth2', uid='2')
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.post(reverse('v1:social_disconnect', args=['google-oauth2']))

    assert response.status_code == 200
    assert UserSocialAuth.objects.filter(user=user).count() == 1


def test_unlinking_a_provider_that_is_not_connected_is_refused(client):
    user = UserFactory()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.post(reverse('v1:social_disconnect', args=['google-oauth2']))

    assert response.status_code == 400


def test_connections_are_listed_for_the_signed_in_user_only(client):
    from social_django.models import UserSocialAuth

    stranger = UserFactory()
    UserSocialAuth.objects.create(user=stranger, provider='google-oauth2', uid='other')

    user = UserFactory()
    UserSocialAuth.objects.create(user=user, provider='linkedin-oauth2', uid='mine')
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    response = client.get(reverse('v1:social_connections'))

    providers = {c['provider'] for c in response.json()['data']['providers']}
    assert providers == {'linkedin-oauth2'}


def test_anonymous_callers_see_nothing(client):
    assert client.get(reverse('v1:social_connections')).status_code in (401, 403)
