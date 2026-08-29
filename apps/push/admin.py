from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'device_name', 'is_active', 'last_seen_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['device_name', 'user__email', 'token']
    readonly_fields = [f.name for f in Device._meta.fields]

    def has_add_permission(self, request):
        # Devices register themselves through the API, which is what keeps a
        # token pointing at exactly one user.
        return False
