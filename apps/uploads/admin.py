from django.contrib import admin

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'original_name',
        'user',
        'purpose',
        'content_type',
        'size_bytes',
        'created_at',
    ]
    list_filter = ['purpose', 'visibility', 'content_type']
    search_fields = ['original_name', 'user__email']
    readonly_fields = [f.name for f in Attachment._meta.fields]

    def has_add_permission(self, request):
        # Uploads go through the API, which is what validates and renames them.
        return False
