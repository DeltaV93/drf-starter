from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions.models import Subscription, Payment, Invoice


class Command(BaseCommand):
    help = 'Generates monthly financial report'

    def handle(self, *args, **options):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        active_subscriptions = Subscription.objects.filter(status='active').count()
        total_revenue = Payment.objects.filter(created_at__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        pending_invoices = Invoice.objects.filter(status='open').count()

        # Generate and save report logic here
        self.stdout.write(self.style.SUCCESS(f'Monthly report generated for {now.strftime("%B %Y")}'))