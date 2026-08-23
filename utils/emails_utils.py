"""Email helpers.

Sending goes through Django's mail API so that settings.EMAIL_BACKEND is
honoured: SES in production, the console backend in development, and locmem
in tests. Do not call boto3 directly here -- that bypasses all three.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .logging_utils import get_logger

logger = get_logger(__name__)


def deliver_email(subject, text_content, html_content, from_email, recipients):
    """Hand a rendered message to the configured backend.

    Raises on failure -- the Celery task needs the exception to retry. Callers
    that must not fail the request go through send_email instead.
    """
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=list(recipients),
    )
    message.attach_alternative(html_content, 'text/html')
    message.send(fail_silently=False)


def send_email(subject, template_name, context, recipient_list, from_email=None):
    """Render an HTML template and send it with a plain-text alternative.

    Returns True if the message was handed off, False otherwise. Failures are
    logged rather than raised so that a mail outage cannot turn a successful
    signup into a 500.

    Rendering always happens here, even when settings.EMAIL_ASYNC moves
    delivery onto Celery: a template that does not render is a bug worth
    surfacing in the request rather than in a worker log, and it keeps model
    instances off the queue, where they would have to be serialised and could
    go stale before the task ran.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    recipients = list(recipient_list)

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    if settings.EMAIL_ASYNC:
        from .tasks import send_rendered_email

        try:
            send_rendered_email.delay(
                subject, text_content, html_content, from_email, recipients
            )
        except Exception:
            # An unreachable broker must not fail the request either.
            logger.exception('Failed to queue %r for %s', subject, ', '.join(recipients))
            return False

        logger.info('Queued %r for %s', subject, ', '.join(recipients))
        return True

    try:
        deliver_email(subject, text_content, html_content, from_email, recipients)
    except Exception:
        logger.exception('Failed to send %r to %s', subject, ', '.join(recipients))
        return False

    logger.info('Sent %r to %s', subject, ', '.join(recipients))
    return True


def send_password_reset_email(user, reset_url):
    return send_email(
        subject='Password reset request',
        template_name='emails/password_reset.html',
        context={'user': user, 'reset_url': reset_url, 'site_name': _site_name()},
        recipient_list=[user.email],
    )


def send_verification_email(user, verification_url):
    return send_email(
        subject='Confirm your email address',
        template_name='emails/verify_email.html',
        context={
            'user': user,
            'verification_url': verification_url,
            'site_name': _site_name(),
        },
        recipient_list=[user.email],
    )


def _site_name():
    return getattr(settings, 'SPECTACULAR_SETTINGS', {}).get('TITLE', 'Our app')
