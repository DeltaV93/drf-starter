from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = (
        'email',
        'account_type',
        'role',
        'email_verified',
        'is_active',
        'is_staff',
    )
    list_filter = ('account_type', 'role', 'email_verified', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'date_deleted', 'last_login', 'date_joined')

    # Spelled out rather than extended from UserAdmin's, which name `username`.
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (
            _('Profile'),
            {'fields': ('phone_number', 'account_type', 'role', 'email_verified')},
        ),
        (_('Audit'), {'fields': ('created_at', 'updated_at', 'date_deleted')}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'usable_password', 'password1', 'password2'),
            },
        ),
        (_('Profile'), {'fields': ('account_type', 'role')}),
    )
