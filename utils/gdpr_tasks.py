"""Building and delivering a data export.

Runs on Celery when EMAIL_ASYNC is on; assembling every section for a busy
account is not something to do inside a request.
"""

from celery import shared_task
from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

from .emails_utils import send_email
from .gdpr_export import build_export, to_json
from .logging_utils import get_logger

logger = get_logger(__name__)

# Namespaced so a signature minted here cannot be replayed against another
# signer in the project.
SIGNER_SALT = 'gdpr-export'


def make_download_token(user):
    return TimestampSigner(salt=SIGNER_SALT).sign(str(user.pk))


def read_download_token(token):
    """Return the user id a token names, or None if it is invalid or stale.

    Signed and time-limited rather than a random row in a table: there is
    nothing to store, nothing to clean up, and a link that has aged out stops
    working without anyone having to expire it.
    """
    try:
        return TimestampSigner(salt=SIGNER_SALT).unsign(
            token, max_age=settings.GDPR_EXPORT_LINK_TIMEOUT
        )
    except (BadSignature, SignatureExpired):
        return None


def deliver_export(user):
    """Email the user a link to their export. Returns True if it was handed off."""
    return send_email(
        subject='Your data export is ready',
        template_name='emails/data_export.html',
        context={
            'user': user,
            'download_url': (
                f'{settings.FRONTEND_URL}/account/export/{make_download_token(user)}'
            ),
            'expiry_hours': settings.GDPR_EXPORT_LINK_TIMEOUT // 3600,
        },
        recipient_list=[user.email],
    )


@shared_task(ignore_result=True)
def send_data_export(user_id):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        logger.info('Export requested for a user that is gone; nothing sent.')
        return

    deliver_export(user)


def request_export(user):
    """Kick off an export, on the queue when there is one."""
    if settings.EMAIL_ASYNC:
        send_data_export.delay(user.pk)
    else:
        deliver_export(user)


def export_json_for(user):
    return to_json(build_export(user))
