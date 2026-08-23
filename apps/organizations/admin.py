from django.contrib import admin

from .models import Invitation, Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ['name']}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['user__email', 'organization__name']
    autocomplete_fields = ['user', 'organization']


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'organization', 'role', 'expires_at', 'accepted_at']
    list_filter = ['role']
    search_fields = ['email', 'organization__name']
    # The digest is not a secret, but showing it invites someone to try using
    # it as one. Nothing here is editable: invitations are created by the API,
    # which is what generates and emails the token.
    readonly_fields = [f.name for f in Invitation._meta.fields]

    def has_add_permission(self, request):
        return False
