"""Drop audit entries past the retention window.

The only sanctioned way rows leave the table. It deletes whole rows by age --
it cannot alter one -- and it uses a queryset delete so the model's own delete
guard does not have to be weakened.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audit.models import AuditEvent


class Command(BaseCommand):
    help = 'Delete audit events older than AUDIT_LOG_RETENTION_DAYS.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=settings.AUDIT_LOG_RETENTION_DAYS,
            help='Override the configured retention window.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without deleting it.',
        )

    def handle(self, *args, **options):
        days = options['days']
        if days <= 0:
            self.stderr.write('Retention must be at least one day; nothing deleted.')
            return

        cutoff = timezone.now() - timedelta(days=days)
        stale = AuditEvent.objects.filter(created_at__lt=cutoff)
        count = stale.count()

        if options['dry_run']:
            self.stdout.write(f'Would delete {count} events older than {cutoff:%Y-%m-%d}.')
            return

        # Queryset delete: bypasses Model.delete by design, which is what keeps
        # the per-row guard absolute everywhere else.
        stale.delete()
        self.stdout.write(f'Deleted {count} events older than {cutoff:%Y-%m-%d}.')
