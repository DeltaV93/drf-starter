from django.contrib import admin

from .models import AddOn, Invoice, Payment, Subscription, SubscriptionPlan, UserAddOn


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'user_limit', 'stripe_price_id', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'stripe_price_id')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'user__email', 'stripe_subscription_id')
    raw_id_fields = ('user',)


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stripe_price_id', 'is_active')
    search_fields = ('name', 'stripe_price_id')


@admin.register(UserAddOn)
class UserAddOnAdmin(admin.ModelAdmin):
    list_display = ('user', 'add_on', 'created_at')
    raw_id_fields = ('user',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('stripe_invoice_id', 'user', 'amount', 'status', 'due_date')
    list_filter = ('status',)
    search_fields = ('stripe_invoice_id', 'user__email')
    raw_id_fields = ('user',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('stripe_payment_intent_id', 'user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('stripe_payment_intent_id', 'user__email')
    raw_id_fields = ('user',)
