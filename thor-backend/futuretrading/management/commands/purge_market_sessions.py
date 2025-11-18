"""
Delete all MarketSession rows. Use with caution.

Usage:
  python manage.py purge_market_sessions --yes-i-am-sure
"""

from django.core.management.base import BaseCommand, CommandError
from FutureTrading.models.MarketSession import MarketSession


class Command(BaseCommand):
    help = "Delete ALL MarketSession rows (single-table design)."

    def add_arguments(self, parser):
        parser.add_argument('--yes-i-am-sure', action='store_true', help='Confirm destructive operation')

    def handle(self, *args, **options):
        if not options.get('yes_i_am_sure'):
            raise CommandError('Refusing to purge without --yes-i-am-sure')

        count = MarketSession.objects.count()
        MarketSession.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {count} MarketSession rows."))
