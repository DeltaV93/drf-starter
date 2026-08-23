"""Storing and serving files."""

from django.conf import settings
from django.core.files.storage import default_storage

from .models import Attachment
from .validators import safe_filename, validate_upload


def store(*, user, uploaded_file, purpose='general', visibility=None, allowed_types=None):
    """Validate and save an upload. Raises ValidationError if it is not acceptable."""
    allowed = set(allowed_types or settings.UPLOAD_ALLOWED_TYPES)
    content_type = validate_upload(
        uploaded_file, allowed_types=allowed, max_bytes=settings.UPLOAD_MAX_BYTES
    )

    attachment = Attachment(
        user=user,
        purpose=purpose,
        stored_name=safe_filename(content_type, uploaded_file.name),
        # Truncated rather than rejected: a silly filename should not fail an
        # otherwise valid upload, and it is display-only.
        original_name=(uploaded_file.name or '')[:255],
        content_type=content_type,
        size_bytes=uploaded_file.size,
        visibility=visibility or Attachment.Visibility.PRIVATE,
    )
    attachment.file.save(attachment.stored_name, uploaded_file, save=False)
    attachment.save()
    return attachment


def url_for(attachment, expires_in=None):
    """A URL the caller can use.

    On S3 this is a signed URL that stops working; on the local filesystem
    backend there is nothing to sign, so it is the plain media URL -- which is
    one reason local storage is a development convenience only.
    """
    expires_in = expires_in or settings.UPLOAD_URL_EXPIRY_SECONDS
    try:
        return default_storage.url(attachment.file.name, expire=expires_in)
    except TypeError:
        # FileSystemStorage.url takes no expiry.
        return attachment.file.url


def delete(attachment):
    """Remove the row and the bytes.

    Both, in that order: an orphaned object in a bucket is invisible and paid
    for indefinitely.
    """
    name = attachment.file.name
    attachment.delete()
    if name and default_storage.exists(name):
        default_storage.delete(name)
