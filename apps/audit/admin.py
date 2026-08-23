from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'actor_label', 'target', 'ip_address']
    list_filter = ['action', 'created_at']
    search_fields = ['actor_label', 'target', 'action']
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    # Read-only in every direction. A log an administrator can edit or delete
    # answers none of the questions it is kept for; retention is the
    # prune_audit_log command, which drops whole rows by age.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
