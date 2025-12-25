from __future__ import annotations
"""
Delete all MarketSession rows. Use with caution.

Usage:
  python manage.py purge_market_sessions --yes-i-am-sure
"""

from django.core.management.base import BaseCommand, CommandError
from ThorTrading.models.MarketSession import MarketSession


class Command(BaseCommand):
    help = "Delete ALL MarketSession rows (single-table design)."

    def add_arguments(self, parser):
        parser.add_argument('--yes-i-am-sure', action='store_true', help='Confirm destructive operation')
        parser.add_argument('--dry-run', action='store_true', help='Show how many rows would be deleted and exit')
        parser.add_argument(
            '--confirm',
            type=str,
            help="Additional confirmation token. Must be 'DELETE' to proceed.",
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')

        count = MarketSession.objects.count()
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: would purge {count} MarketSession rows."))
            return

        if not options.get('yes_i_am_sure'):
            raise CommandError('Refusing to purge without --yes-i-am-sure')

        confirm_token = options.get('confirm')
        if confirm_token != 'DELETE':
            raise CommandError("Refusing to purge without --confirm DELETE")

        MarketSession.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {count} MarketSession rows."))

