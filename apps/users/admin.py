from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        'username',
        'email',
        'account_type',
        'role',
        'email_verified',
        'is_active',
        'is_staff',
    )
    list_filter = ('account_type', 'role', 'email_verified', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'date_deleted', 'last_login', 'date_joined')

    fieldsets = (
        *UserAdmin.fieldsets,
        (
            _('Profile'),
            {'fields': ('phone_number', 'account_type', 'role', 'email_verified')},
        ),
        (_('Audit'), {'fields': ('created_at', 'updated_at', 'date_deleted')}),
    )

    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        (_('Profile'), {'fields': ('email', 'account_type', 'role')}),
    )
