from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.subscriptions.models import Invoice, Payment, Subscription


class Command(BaseCommand):
    help = 'Summarise subscriptions, revenue and outstanding invoices for the current month'

    def handle(self, *args, **options):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        active_subscriptions = Subscription.objects.filter(
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
        ).count()

        total_revenue = (
            Payment.objects.filter(created_at__gte=month_start, status='succeeded').aggregate(
                total=Sum('amount')
            )['total']
            or 0
        )

        pending_invoices = Invoice.objects.filter(status='open').count()

        self.stdout.write(self.style.SUCCESS(f'Report for {now.strftime("%B %Y")}'))
        self.stdout.write(f'  Active subscriptions: {active_subscriptions}')
        # Formatted explicitly: SQLite and Postgres disagree on how a summed
        # DecimalField renders, and the report should not.
        self.stdout.write(f'  Revenue this month:   {Decimal(total_revenue):.2f}')
        self.stdout.write(f'  Open invoices:        {pending_invoices}')
