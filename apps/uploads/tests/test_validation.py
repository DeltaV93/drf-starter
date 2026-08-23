"""What an upload has to prove before it is stored.

The filename, the extension and the Content-Type header all come from the
uploader. Every test here is about not believing any of them.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.uploads import services
from apps.uploads.validators import safe_filename, sniff_content_type, validate_upload
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
JPEG = b'\xff\xd8\xff' + b'\x00' * 64
PDF = b'%PDF-1.7\n' + b'\x00' * 64
SCRIPT = b'#!/bin/sh\nrm -rf /\n'
HTML = b'<html><script>alert(1)</script></html>'

ALLOWED = {'image/jpeg', 'image/png', 'application/pdf'}


def _upload(content, name='file.png', content_type='image/png'):
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_the_type_comes_from_the_bytes_not_the_header():
    """A shell script announced as image/png is a shell script."""
    uploaded = _upload(SCRIPT, name='avatar.png', content_type='image/png')

    with pytest.raises(ValidationError):
        validate_upload(uploaded, allowed_types=ALLOWED, max_bytes=1_000_000)


def test_html_disguised_as_an_image_is_refused():
    """Stored HTML served back is stored XSS."""
    uploaded = _upload(HTML, name='photo.png', content_type='image/png')

    with pytest.raises(ValidationError):
        validate_upload(uploaded, allowed_types=ALLOWED, max_bytes=1_000_000)


def test_a_real_image_with_a_lying_extension_is_accepted_for_what_it_is():
    uploaded = _upload(PNG, name='definitely.pdf', content_type='application/pdf')

    assert validate_upload(uploaded, allowed_types=ALLOWED, max_bytes=1_000_000) == 'image/png'


def test_a_recognised_type_that_is_not_allowed_is_refused():
    uploaded = _upload(PDF, name='doc.pdf', content_type='application/pdf')

    with pytest.raises(ValidationError, match='application/pdf'):
        validate_upload(uploaded, allowed_types={'image/png'}, max_bytes=1_000_000)


def test_an_oversized_file_is_refused():
    uploaded = _upload(PNG + b'\x00' * 5000)

    with pytest.raises(ValidationError, match='limit'):
        validate_upload(uploaded, allowed_types=ALLOWED, max_bytes=100)


def test_an_empty_file_is_refused():
    uploaded = _upload(b'')

    with pytest.raises(ValidationError, match='empty'):
        validate_upload(uploaded, allowed_types=ALLOWED, max_bytes=1_000_000)


def test_sniffing_leaves_the_file_readable():
    """Consuming the stream would store an empty file."""
    uploaded = _upload(PNG)

    sniff_content_type(uploaded)

    assert uploaded.read() == PNG


@pytest.mark.parametrize(
    'hostile_name',
    [
        '../../../../etc/passwd',
        '..\\..\\windows\\system32\\config',
        'file\x00.png',
        'a' * 500 + '.png',
        'invoice‮gnp.exe',
        '.htaccess',
    ],
)
def test_the_uploaded_name_is_never_used_as_a_path(hostile_name):
    """Generated, not sanitised: traversal, null bytes, a right-to-left
    override that makes `exe` read as `gpj`, a name long enough to break a
    filesystem -- none of it survives."""
    name = safe_filename('image/png', hostile_name)

    assert '/' not in name
    assert '\\' not in name
    assert '\x00' not in name
    assert '‮' not in name
    assert name.endswith('.png')
    assert len(name) < 64


def test_the_extension_follows_the_sniffed_type():
    assert safe_filename('image/jpeg', 'thing.png').endswith('.jpg')
    assert safe_filename('application/pdf', 'thing.png').endswith('.pdf')


def test_two_uploads_never_collide():
    names = {safe_filename('image/png') for _ in range(200)}

    assert len(names) == 200


def test_a_stored_file_keeps_the_original_name_for_display_only():
    user = UserFactory()

    attachment = services.store(user=user, uploaded_file=_upload(PNG, name='holiday snap.png'))

    assert attachment.original_name == 'holiday snap.png'
    # ...but the path is built from the generated name.
    assert 'holiday' not in attachment.file.name
    assert attachment.stored_name in attachment.file.name
