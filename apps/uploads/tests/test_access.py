"""Who can reach a stored file.

Ownership is checked in the view rather than trusted to an unguessable path.
A URL that leaks stays valid forever; a permission check does not.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.uploads import services
from apps.uploads.models import Attachment
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


def _store(user, **kwargs):
    return services.store(
        user=user,
        uploaded_file=SimpleUploadedFile('x.png', PNG, content_type='image/png'),
        **kwargs,
    )


def test_uploading_and_listing_your_own(signed_in):
    client, user = signed_in()

    response = client.post(
        reverse('v1:attachment_list'),
        {'file': SimpleUploadedFile('x.png', PNG, content_type='image/png')},
    )

    assert response.status_code == 201, response.content
    body = response.json()['data']
    assert body['content_type'] == 'image/png'
    assert body['visibility'] == 'private'
    # The storage path is not something a client should hold.
    assert 'file' not in body
    assert Attachment.objects.filter(user=user).count() == 1


def test_the_listing_shows_only_your_own(signed_in):
    stranger = UserFactory()
    _store(stranger)
    client, user = signed_in()
    _store(user)

    response = client.get(reverse('v1:attachment_list'))

    assert len(response.json()['data']) == 1


def test_a_private_file_is_not_reachable_by_someone_else(signed_in):
    stranger = UserFactory()
    theirs = _store(stranger)
    client, _user = signed_in()

    response = client.get(reverse('v1:attachment_download', args=[theirs.pk]))

    assert response.status_code == 404


def test_a_private_file_is_reachable_by_its_owner(signed_in):
    client, user = signed_in()
    mine = _store(user)

    response = client.get(reverse('v1:attachment_download', args=[mine.pk]))

    assert response.status_code == 302


def test_a_public_file_is_reachable_by_any_signed_in_user(signed_in):
    owner = UserFactory()
    shared = _store(owner, visibility=Attachment.Visibility.PUBLIC)
    client, _user = signed_in()

    response = client.get(reverse('v1:attachment_download', args=[shared.pk]))

    assert response.status_code == 302


def test_anonymous_callers_reach_nothing(client):
    owner = UserFactory()
    shared = _store(owner, visibility=Attachment.Visibility.PUBLIC)

    assert client.get(reverse('v1:attachment_list')).status_code in (401, 403)
    assert client.get(reverse('v1:attachment_download', args=[shared.pk])).status_code in (
        401,
        403,
    )


def test_you_cannot_delete_someone_elses_file(signed_in):
    stranger = UserFactory()
    theirs = _store(stranger)
    client, _user = signed_in()

    response = client.delete(reverse('v1:attachment_detail', args=[theirs.pk]))

    assert response.status_code == 404
    assert Attachment.objects.filter(pk=theirs.pk).exists()


def test_deleting_removes_the_bytes_as_well_as_the_row(signed_in):
    """An orphaned object in a bucket is invisible and paid for indefinitely."""
    from django.core.files.storage import default_storage

    client, user = signed_in()
    mine = _store(user)
    stored_path = mine.file.name
    assert default_storage.exists(stored_path)

    response = client.delete(reverse('v1:attachment_detail', args=[mine.pk]))

    assert response.status_code == 200
    assert not Attachment.objects.filter(pk=mine.pk).exists()
    assert not default_storage.exists(stored_path)


def test_a_rejected_upload_stores_nothing(signed_in):
    client, user = signed_in()

    response = client.post(
        reverse('v1:attachment_list'),
        {'file': SimpleUploadedFile('x.png', b'#!/bin/sh\n', content_type='image/png')},
    )

    assert response.status_code == 400
    assert Attachment.objects.filter(user=user).count() == 0


def test_uploading_without_a_file_is_a_clear_error(signed_in):
    client, _user = signed_in()

    response = client.post(reverse('v1:attachment_list'), {})

    assert response.status_code == 400
    assert 'file' in response.json()['message']


def test_files_are_partitioned_by_user(signed_in):
    """One directory accumulating everything is a problem at scale."""
    first = UserFactory()
    second = UserFactory()

    a = _store(first)
    b = _store(second)

    assert str(first.pk) in a.file.name
    assert str(second.pk) in b.file.name
    assert a.file.name != b.file.name
