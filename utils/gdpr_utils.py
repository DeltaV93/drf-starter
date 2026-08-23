"""GDPR helpers.

Account deletion anonymizes rather than hard-deletes: related rows (invoices,
payments, audit history) stay referentially intact while every field that
identifies a person is overwritten.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from .logging_utils import get_logger

logger = get_logger(__name__)

# Fields cleared to their empty value if the user model defines them. Add
# project-specific personal data fields here as the model grows.
OPTIONAL_PERSONAL_FIELDS = ('phone_number',)


@transaction.atomic
def anonymize_user_data(user):
    """Overwrite a user's personal data in place and deactivate the account.

    Idempotent: re-running on an already anonymized user is a no-op.
    """
    if getattr(user, 'date_deleted', None):
        logger.info('User %s is already anonymized; skipping.', user.pk)
        return user

    unique_id = uuid.uuid4().hex[:12]

    user.username = f'deleted_user_{unique_id}'
    user.email = f'{unique_id}@deleted.invalid'
    user.first_name = 'Deleted'
    user.last_name = 'User'

    for field in OPTIONAL_PERSONAL_FIELDS:
        if hasattr(user, field):
            setattr(user, field, '')

    # Unusable password, not a random one: the account must not be reachable
    # via a password reset afterwards.
    user.set_unusable_password()

    user.is_active = False
    user.date_deleted = timezone.now()

    user.save()

    # Drop every active session so the anonymized account is logged out
    # everywhere, not just in the browser that made the request.
    _delete_sessions_for_user(user)

    logger.info('Anonymized user %s', user.pk)
    return user


def _delete_sessions_for_user(user):
    from django.contrib.sessions.models import Session

    user_pk = str(user.pk)
    for session in Session.objects.iterator():
        if session.get_decoded().get('_auth_user_id') == user_pk:
            session.delete()
