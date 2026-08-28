from django.contrib import admin
from .models import DocumentVault, Document, DocumentVersion


@admin.register(DocumentVault)
class DocumentVaultAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('filename',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('document__filename',)
