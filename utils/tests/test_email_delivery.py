"""How send_email hands a message off, synchronously and via Celery.

EMAIL_ASYNC only moves *delivery*. Rendering stays in the caller either way,
so these assert that a template error surfaces to the caller rather than
disappearing into a worker, and that a broker or backend failure never turns a
successful signup into a 500.

CELERY_TASK_ALWAYS_EAGER is on in testing.py, so .delay() runs inline here --
which exercises the task body, not the queue.
"""

from unittest.mock import patch

import pytest
from django.core import mail
from django.template import TemplateDoesNotExist

from utils.emails_utils import send_email

CONTEXT = {'user': None, 'reset_url': 'https://example.com/r/abc', 'site_name': 'Test'}


def _send(**overrides):
    kwargs = {
        'subject': 'Hello',
        'template_name': 'emails/password_reset.html',
        'context': CONTEXT,
        'recipient_list': ['someone@example.com'],
    }
    kwargs.update(overrides)
    return send_email(**kwargs)


@pytest.mark.parametrize('async_enabled', [False, True])
def test_the_message_is_delivered_either_way(settings, async_enabled):
    settings.EMAIL_ASYNC = async_enabled

    assert _send() is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['someone@example.com']
    assert mail.outbox[0].subject == 'Hello'


@pytest.mark.parametrize('async_enabled', [False, True])
def test_both_parts_are_attached(settings, async_enabled):
    """A text body plus an HTML alternative, not one or the other."""
    settings.EMAIL_ASYNC = async_enabled

    _send()

    message = mail.outbox[0]
    assert message.body  # plain text
    assert message.alternatives
    content, mimetype = message.alternatives[0]
    assert mimetype == 'text/html'
    assert '<' in content


@pytest.mark.parametrize('async_enabled', [False, True])
def test_a_broken_template_raises_rather_than_being_swallowed(settings, async_enabled):
    """Rendering is the caller's problem, in both modes.

    If this were deferred to the task, a typo in a template would show up as a
    silent non-delivery in a worker log instead of a failure anyone notices.
    """
    settings.EMAIL_ASYNC = async_enabled

    with pytest.raises(TemplateDoesNotExist):
        _send(template_name='emails/does_not_exist.html')

    assert mail.outbox == []


def test_a_backend_failure_is_reported_not_raised(settings):
    """A mail outage must not turn a successful signup into a 500."""
    settings.EMAIL_ASYNC = False

    with patch(
        'django.core.mail.EmailMultiAlternatives.send', side_effect=OSError('smtp down')
    ):
        assert _send() is False


def test_an_unreachable_broker_is_reported_not_raised(settings):
    """Same contract when the queue is what is broken."""
    settings.EMAIL_ASYNC = True

    with patch('utils.tasks.send_rendered_email.delay', side_effect=OSError('broker down')):
        assert _send() is False

    assert mail.outbox == []


def test_only_strings_are_put_on_the_queue(settings):
    """Nothing that needs pickling, and nothing that can go stale.

    The task signature is the queue contract: a model instance here would
    either fail to serialise under the JSON serializer the project pins, or
    arrive describing a row that has since changed.
    """
    settings.EMAIL_ASYNC = True

    with patch('utils.tasks.send_rendered_email.delay') as delay:
        _send()

    (args, kwargs) = delay.call_args
    assert kwargs == {}
    subject, text, html, from_email, recipients = args
    assert isinstance(subject, str)
    assert isinstance(text, str)
    assert isinstance(html, str)
    assert isinstance(from_email, str)
    assert recipients == ['someone@example.com']
    assert all(isinstance(r, str) for r in recipients)
