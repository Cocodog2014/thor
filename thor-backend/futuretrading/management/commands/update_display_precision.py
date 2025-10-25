"""
Management command to update display_precision for futures instruments.

Usage:
    python manage.py update_display_precision --symbol YM --precision 0
    python manage.py update_display_precision --symbol ES --precision 2
    python manage.py update_display_precision --all
"""

from django.core.management.base import BaseCommand
from FutureTrading.models import TradingInstrument


class Command(BaseCommand):
    help = 'Update display_precision for trading instruments'

    # Standard precision values for common futures
    STANDARD_PRECISION = {
        'YM': 0,   # Dow Jones - whole points
        'ES': 2,   # S&P 500 - 0.25 point increments (2 decimals)
        'NQ': 2,   # Nasdaq 100 - 0.25 point increments (2 decimals)
        'RTY': 2,  # Russell 2000 - 0.10 point increments (2 decimals)
        'RT': 2,   # Russell 2000 (alias) - 0.10 point increments (2 decimals)
        'CL': 2,   # Crude Oil - 0.01 (2 decimals)
        'SI': 3,   # Silver - 0.005 (3 decimals)
        'HG': 4,   # Copper - 0.0005 (4 decimals)
        'GC': 1,   # Gold - 0.10 (1 decimal)
        'VX': 2,   # VIX - 0.05 (2 decimals)
        'DX': 2,   # Dollar Index - 0.01 (2 decimals)
        'ZB': 2,   # 30-Year Treasury - 1/32nd displayed as decimal (2 decimals)
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Symbol to update (e.g., YM, ES, NQ)',
        )
        parser.add_argument(
            '--precision',
            type=int,
            help='Number of decimal places to display',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all instruments with standard precision values',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        symbol = options.get('symbol')
        precision = options.get('precision')
        update_all = options.get('all')
        dry_run = options.get('dry_run')

        if update_all:
            self.update_all_instruments(dry_run)
        elif symbol and precision is not None:
            self.update_single_instrument(symbol, precision, dry_run)
        else:
            self.stdout.write(self.style.ERROR(
                'Please provide either --symbol and --precision, or --all'
            ))
            return

    def update_single_instrument(self, symbol, precision, dry_run):
        """Update a single instrument's display precision."""
        # Try with and without leading slash
        instruments = TradingInstrument.objects.filter(
            symbol__in=[symbol, f'/{symbol}', symbol.lstrip('/')]
        )

        if not instruments.exists():
            self.stdout.write(self.style.ERROR(
                f'Instrument with symbol "{symbol}" not found'
            ))
            return

        for instrument in instruments:
            old_precision = instrument.display_precision
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'[DRY RUN] Would update {instrument.symbol}: '
                    f'{old_precision} → {precision}'
                ))
            else:
                instrument.display_precision = precision
                instrument.save()
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Updated {instrument.symbol}: '
                    f'{old_precision} → {precision} decimal places'
                ))

    def update_all_instruments(self, dry_run):
        """Update all instruments with standard precision values."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Updating display precision for all futures instruments...\n'
        ))

        updated_count = 0
        not_found = []

        for symbol, precision in self.STANDARD_PRECISION.items():
            # Try with and without leading slash
            instruments = TradingInstrument.objects.filter(
                symbol__in=[symbol, f'/{symbol}']
            )

            if not instruments.exists():
                not_found.append(symbol)
                continue

            for instrument in instruments:
                old_precision = instrument.display_precision
                if old_precision != precision:
                    if dry_run:
                        self.stdout.write(self.style.WARNING(
                            f'[DRY RUN] Would update {instrument.symbol}: '
                            f'{old_precision} → {precision}'
                        ))
                    else:
                        instrument.display_precision = precision
                        instrument.save()
                        self.stdout.write(self.style.SUCCESS(
                            f'✓ Updated {instrument.symbol}: '
                            f'{old_precision} → {precision} decimal places'
                        ))
                    updated_count += 1
                else:
                    self.stdout.write(
                        f'  {instrument.symbol}: already at {precision} decimals (no change)'
                    )

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Would update {updated_count} instrument(s)'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Updated {updated_count} instrument(s)'
            ))

        if not_found:
            self.stdout.write(self.style.WARNING(
                f'\nInstruments not found in database: {", ".join(not_found)}'
            ))

        # Show current settings
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Current precision settings:'))
        all_instruments = TradingInstrument.objects.filter(is_active=True).order_by('symbol')
        for inst in all_instruments:
            self.stdout.write(f'  {inst.symbol:10s} → {inst.display_precision} decimal places')
