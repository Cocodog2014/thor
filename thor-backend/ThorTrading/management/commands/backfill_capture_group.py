from django.core.management.base import BaseCommand
from django.db import transaction

from ThorTrading.models.MarketSession import MarketSession


class Command(BaseCommand):
    help = "Backfill capture_group for existing MarketSession rows (assign session_number where null)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='Show counts only without performing updates'
        )

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        qs_base = MarketSession.objects.filter(capture_group__isnull=True)
        total = qs_base.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No rows require backfill.'))
            return
        self.stdout.write(f'Rows needing backfill: {total}')
        if dry:
            self.stdout.write('Dry-run mode; no changes applied.')
            return
        updated = 0
        batch_size = 5000
        with transaction.atomic():
            while True:
                batch = list(
                    MarketSession.objects
                    .filter(capture_group__isnull=True)
                    .values_list('pk', 'session_number')[:batch_size]
                )
                if not batch:
                    break
                for pk, session_number in batch:
                    MarketSession.objects.filter(pk=pk).update(capture_group=session_number)
                updated += len(batch)
        self.stdout.write(self.style.SUCCESS(f'Backfilled capture_group on {updated} rows.'))
        remaining = MarketSession.objects.filter(capture_group__isnull=True).count()
        if remaining:
            self.stdout.write(self.style.WARNING(f'{remaining} rows still null (investigate).'))
        else:
            self.stdout.write(self.style.SUCCESS('All rows now have capture_group.'))

