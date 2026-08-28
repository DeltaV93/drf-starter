from django.contrib import admin
from .models import Trip, TripHome


class TripHomeInline(admin.TabularInline):
    model = TripHome
    extra = 1


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TripHomeInline]


@admin.register(TripHome)
class TripHomeAdmin(admin.ModelAdmin):
    list_display = ('address', 'trip', 'visit_order', 'price')
    list_filter = ('created_at',)
    search_fields = ('address',)
