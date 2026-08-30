"""Scheduled maintenance for the token blacklist.

Refresh rotation is what makes a month-long session safe: every refresh mints
a new pair and blacklists the one just spent. The cost is a row per refresh —
with a fifteen-minute access token that is roughly a hundred rows per device
per day, forever, and nothing removes them.

`flushexpiredtokens` is SimpleJWT's own command and it only deletes tokens
that have already expired, so a blacklisted token stays enforceable for its
whole lifetime. Running it is safe at any hour; not running it is a table that
grows until someone notices the database bill.
"""

from celery import shared_task
from django.core.management import call_command

from utils.logging_utils import get_logger

logger = get_logger(__name__)


@shared_task(ignore_result=True)
def flush_expired_tokens():
    """Delete blacklisted refresh tokens that have expired anyway.

    Scheduled by CELERY_BEAT_SCHEDULE in template/settings/base.py. Wrapped in
    a task rather than left to a cron entry on the host so it travels with the
    application: a deployment that runs a worker gets the cleanup, and one
    that does not was never going to have a cron entry either.
    """
    call_command('flushexpiredtokens')
    logger.info('Flushed expired blacklisted refresh tokens.')
