from django.contrib import admin

from .models import ConnectedServer


@admin.register(ConnectedServer)
class ConnectedServerAdmin(admin.ModelAdmin):
    list_display = ('user', 'slug', 'enabled', 'last_used_at', 'created_at')
    list_filter = ('enabled', 'slug')
    search_fields = ('user__email', 'user__username', 'slug')
    # The credential is never shown, not even encrypted. An admin reading a
    # ciphertext out of a form is a copy of it somewhere it need not be.
    exclude = ('encrypted_credential',)
    readonly_fields = ('created_at', 'updated_at', 'last_used_at')
