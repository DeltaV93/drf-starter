from django.contrib import admin
from .models import ShareLink, ShareLinkDocument, ShareSession


class ShareLinkDocumentInline(admin.TabularInline):
    model = ShareLinkDocument
    extra = 1


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ('token', 'vault', 'expires_at', 'created_at')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('token', 'vault__user__email')
    readonly_fields = ('token', 'created_at')
    inlines = [ShareLinkDocumentInline]


@admin.register(ShareSession)
class ShareSessionAdmin(admin.ModelAdmin):
    list_display = ('share_link', 'expires_at', 'created_at')
    list_filter = ('created_at', 'expires_at')
    readonly_fields = ('access_token', 'created_at')
