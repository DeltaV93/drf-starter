from django.contrib import admin

from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'prefix', 'scope', 'last_used_at', 'revoked_at']
    list_filter = ['scope']
    search_fields = ['name', 'prefix', 'user__email']
    # Nothing here is editable. Keys are minted by the API, which is what
    # generates the secret and shows it once; an admin who could change a
    # scope could silently upgrade someone else's credential.
    readonly_fields = [f.name for f in APIKey._meta.fields]
    actions = ['revoke_selected']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Revoke selected keys')
    def revoke_selected(self, request, queryset):
        for key in queryset:
            key.revoke()
