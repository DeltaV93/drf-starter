"""Celery tasks for the shared helpers.

Autodiscovery walks INSTALLED_APPS, and `utils` is not an app, so
`template/celery.py` names this package explicitly.
"""

from celery import shared_task

from .logging_utils import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True,
    ignore_result=True,
    # A mail provider being briefly unreachable is the common case and is worth
    # retrying; a malformed address is not, but the backend raises the same way
    # for both, so cap the attempts rather than trying to tell them apart.
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_rendered_email(self, subject, text_content, html_content, from_email, recipients):
    """Deliver an already-rendered message.

    Only strings cross the queue boundary. Rendering happens in the caller so
    that a broken template fails the request that caused it, and so no model
    instance has to be serialised or re-fetched here.
    """
    from .emails_utils import deliver_email

    deliver_email(subject, text_content, html_content, from_email, recipients)
    logger.info('Sent %r to %s', subject, ', '.join(recipients))
