from rest_framework import serializers

from .models import AddOn, Invoice, Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'name', 'stripe_price_id', 'user_limit', 'price')


class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = ('id', 'name', 'stripe_price_id', 'price')


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'plan', 'status', 'current_period_end', 'is_current')


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'stripe_invoice_id', 'amount', 'status', 'due_date', 'pdf_url')
