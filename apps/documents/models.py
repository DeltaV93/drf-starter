from django.db import models
from django.conf import settings


class DocumentVault(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_vault')
    key_derivation_salt = models.BinaryField()
    encrypted_master_key = models.BinaryField()
    master_key_nonce = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Vault for {self.user.email}'


class Document(models.Model):
    CATEGORIES = [
        ('receipts', 'Receipts'),
        ('mortgage', 'Mortgage'),
        ('offer_letter', 'Offer Letter'),
        ('inspection', 'Inspection'),
        ('appraisal', 'Appraisal'),
        ('title', 'Title'),
        ('other', 'Other'),
    ]

    vault = models.ForeignKey(DocumentVault, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    encrypted_file_key = models.BinaryField()
    storage_path = models.CharField(max_length=500)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['vault', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.filename} ({self.category})'


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    storage_path = models.CharField(max_length=500)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f'{self.document.filename} v{self.version_number}'
