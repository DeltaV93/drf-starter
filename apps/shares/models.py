from django.db import models
from apps.documents.models import DocumentVault, Document


class ShareLink(models.Model):
    vault = models.ForeignKey(DocumentVault, on_delete=models.CASCADE, related_name='shares')
    token = models.CharField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['token', 'expires_at']),
        ]

    def __str__(self):
        return f'Share: {self.token[:10]}...'


class ShareLinkDocument(models.Model):
    share_link = models.ForeignKey(ShareLink, on_delete=models.CASCADE, related_name='share_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('share_link', 'document')

    def __str__(self):
        return f'{self.share_link.token[:10]}... -> {self.document.filename}'


class ShareSession(models.Model):
    share_link = models.ForeignKey(ShareLink, on_delete=models.CASCADE, related_name='sessions')
    access_token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Session: {self.access_token[:10]}...'
