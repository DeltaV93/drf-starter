from unittest.mock import patch

import pytest
from django.core import mail

from apps.users.factories import UserFactory
from utils.emails_utils import send_email, send_password_reset_email

pytestmark = pytest.mark.django_db


def test_send_email_uses_the_configured_backend():
    # Sending must go through Django's mail API, not straight to boto3 --
    # otherwise EMAIL_BACKEND (console locally, locmem here) is bypassed.
    sent = send_email(
        subject='Hello',
        template_name='emails/password_reset.html',
        context={'user': UserFactory(), 'reset_url': 'https://example.com/r'},
        recipient_list=['someone@example.com'],
    )

    assert sent is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == 'Hello'


def test_send_email_attaches_an_html_alternative():
    send_email(
        subject='Hello',
        template_name='emails/password_reset.html',
        context={'user': UserFactory(), 'reset_url': 'https://example.com/r'},
        recipient_list=['someone@example.com'],
    )

    content, mimetype = mail.outbox[0].alternatives[0]
    assert mimetype == 'text/html'
    assert 'https://example.com/r' in content


def test_the_plain_text_body_is_not_html():
    send_email(
        subject='Hello',
        template_name='emails/password_reset.html',
        context={'user': UserFactory(), 'reset_url': 'https://example.com/r'},
        recipient_list=['someone@example.com'],
    )

    assert '<a href' not in mail.outbox[0].body


def test_a_delivery_failure_is_reported_not_raised():
    with patch(
        'django.core.mail.EmailMultiAlternatives.send', side_effect=OSError('smtp down')
    ):
        sent = send_password_reset_email(UserFactory(), 'https://example.com/r')

    # A mail outage must not turn a successful signup into a 500.
    assert sent is False
