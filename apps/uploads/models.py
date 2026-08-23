"""Stored files.

Scoped to a user, like every other optional feature, so this app holds no
foreign key into any of the others.

Private by default. A file is reached through a view that checks who is asking
and then hands back a time-limited URL, rather than by a guessable path anyone
who learns it can share.
"""

from django.conf import settings
from django.db import models

from .validators import upload_path


class Attachment(models.Model):
    """A file belonging to a user.

    `purpose` is a plain string rather than a relation: it lets the same table
    serve an avatar, an invoice attachment and whatever the project adds later,
    without this app knowing about any of them.
    """

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        PUBLIC = 'public', 'Public'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attachments'
    )
    purpose = models.CharField(max_length=64, default='general', db_index=True)

    file = models.FileField(upload_to=upload_path, max_length=255)

    # The name generated at save time. Kept as a column so upload_path can use
    # it without ever consulting what the client sent.
    stored_name = models.CharField(max_length=255)
    # What the uploader called it -- for display only. Never used to build a
    # path, and escaped wherever it is rendered.
    original_name = models.CharField(max_length=255, blank=True, default='')

    # Sniffed from the file's own bytes, not from the Content-Type header.
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()

    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_name or self.stored_name} ({self.user})'

    def storage_prefix(self):
        """Partition by user, so one directory does not accumulate everything."""
        return f'{self.purpose}/{self.user_id}'

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC
