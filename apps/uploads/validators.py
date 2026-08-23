"""Deciding whether an uploaded file is what it claims to be.

Every check here treats the client as hostile. The filename, the extension and
the Content-Type header all come from the uploader and mean nothing on their
own -- a file called avatar.png with an image/png header can be a shell script,
an HTML page carrying script, or a 4GB zip bomb.
"""

import mimetypes
import secrets
from pathlib import Path

from django.core.exceptions import ValidationError

# Content sniffed from the first bytes, not from the header or the extension.
# Kept deliberately short: a template that accepts everything is a template
# that accepts the thing you did not think about.
MAGIC_SIGNATURES = (
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
    (b'%PDF-', 'application/pdf'),
)

# WebP and other RIFF containers need two checks, so they are handled apart.
RIFF_PREFIX = b'RIFF'
WEBP_MARKER = b'WEBP'

EXTENSION_FOR = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'application/pdf': '.pdf',
}

# How much has to be read to identify a file. Small, so a hostile upload
# cannot make identification itself expensive.
SNIFF_BYTES = 32


def sniff_content_type(uploaded_file):
    """Identify a file from its own bytes, or None if unrecognised.

    Returning None for anything unknown is the point: an allow-list of formats
    we can actually name, rather than a deny-list of the ones we thought of.
    """
    position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(SNIFF_BYTES)
    finally:
        uploaded_file.seek(position)

    for signature, content_type in MAGIC_SIGNATURES:
        if header.startswith(signature):
            return content_type

    if header.startswith(RIFF_PREFIX) and header[8:12] == WEBP_MARKER:
        return 'image/webp'

    return None


def validate_upload(uploaded_file, *, allowed_types, max_bytes):
    """Return the sniffed content type, or raise ValidationError.

    Size is checked before anything else so a huge file is rejected without
    being read.
    """
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f'That file is {uploaded_file.size // 1024}KB; the limit is {max_bytes // 1024}KB.'
        )
    if uploaded_file.size == 0:
        raise ValidationError('That file is empty.')

    content_type = sniff_content_type(uploaded_file)
    if content_type is None:
        raise ValidationError(
            'That file type is not recognised. Allowed: '
            + ', '.join(sorted(allowed_types))
            + '.'
        )
    if content_type not in allowed_types:
        # Names what the file *is*, not what it was labelled, so the message
        # is useful when the two disagree.
        raise ValidationError(
            f'That file is a {content_type}. Allowed: '
            + ', '.join(sorted(allowed_types))
            + '.'
        )

    return content_type


def safe_filename(content_type, original_name=''):
    """A generated name with an extension derived from the sniffed type.

    The uploaded name is never reused, not even sanitised: it can carry path
    traversal, a null byte, a second extension, a name long enough to break a
    filesystem, or a Unicode right-to-left override that makes `exe` look like
    `gpj`. Keeping the original is a product decision -- store it in a column,
    not in the path.
    """
    del original_name  # Deliberately unused; see above.
    extension = (
        EXTENSION_FOR.get(content_type) or mimetypes.guess_extension(content_type) or ''
    )
    return f'{secrets.token_hex(16)}{extension}'


def upload_path(instance, filename):
    """Where a file lands. Never influenced by the uploaded name."""
    del filename
    return str(Path('uploads') / instance.storage_prefix() / instance.stored_name)
