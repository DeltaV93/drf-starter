from django.contrib import admin

from .models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ['platform', 'minimum_version', 'recommended_version', 'updated_at']
    list_filter = ['platform']

    fieldsets = [
        (
            None,
            {
                'fields': ['platform', 'store_url'],
            },
        ),
        (
            'Version floors',
            {
                'fields': ['minimum_version', 'recommended_version'],
                'description': (
                    'Leave both empty and nothing is gated. '
                    '<strong>minimum_version blocks the app outright</strong> for anyone '
                    'below it, so reach for recommended_version first and keep the '
                    'minimum for the cases where letting the old build keep running is '
                    'worse than interrupting someone.'
                ),
            },
        ),
        ('Wording', {'fields': ['message']}),
    ]
    readonly_fields = ['updated_at']
