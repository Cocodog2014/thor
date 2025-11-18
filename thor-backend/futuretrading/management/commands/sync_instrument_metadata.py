"""
Unified management command to sync all instrument metadata.

Replaces: populate_trading_values.py + update_display_precision.py

Usage:
    python manage.py sync_instrument_metadata              # Update all instruments
    python manage.py sync_instrument_metadata --symbol YM  # Update one symbol
    python manage.py sync_instrument_metadata --dry-run    # Preview changes
"""

from django.core.management.base import BaseCommand
from FutureTrading.models import TradingInstrument
from decimal import Decimal


class Command(BaseCommand):
    help = 'Sync display precision, tick values, and margin requirements for trading instruments'

    # Complete metadata for all futures in one place
    INSTRUMENT_METADATA = {
        'YM': {
            'display_precision': 0,  # Whole points
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('17000.00'),
        },
        'ES': {
            'display_precision': 2,  # 0.25 increments
            'tick_value': Decimal('12.50'),
            'margin_requirement': Decimal('13000.00'),
        },
        'NQ': {
            'display_precision': 2,  # 0.25 increments
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('16000.00'),
        },
        'RTY': {
            'display_precision': 2,  # 0.10 increments
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('7500.00'),
        },
        'RT': {
            'display_precision': 2,  # Alias for RTY
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('7500.00'),
        },
        'CL': {
            'display_precision': 2,  # 0.01
            'tick_value': Decimal('10.00'),
            'margin_requirement': Decimal('8000.00'),
        },
        'GC': {
            'display_precision': 1,  # 0.10
            'tick_value': Decimal('10.00'),
            'margin_requirement': Decimal('11000.00'),
        },
        'SI': {
            'display_precision': 3,  # 0.005
            'tick_value': Decimal('25.00'),
            'margin_requirement': Decimal('14000.00'),
        },
        'HG': {
            'display_precision': 4,  # 0.0005
            'tick_value': Decimal('12.50'),
            'margin_requirement': Decimal('4000.00'),
        },
        'VX': {
            'display_precision': 2,  # 0.05
            'tick_value': Decimal('50.00'),
            'margin_requirement': Decimal('6000.00'),
        },
        'DX': {
            'display_precision': 2,  # 0.01
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('2500.00'),
        },
        'ZB': {
            'display_precision': 2,  # 1/32nd as decimal
            'tick_value': Decimal('31.25'),
            'margin_requirement': Decimal('5000.00'),
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Update single symbol (e.g., YM, ES, NQ)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving',
        )

    def handle(self, *args, **options):
        symbol = options.get('symbol')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ===\n'))

        if symbol:
            self.update_single_instrument(symbol, dry_run)
        else:
            self.update_all_instruments(dry_run)

    def update_single_instrument(self, symbol, dry_run):
        """Update metadata for a single instrument."""
        metadata = self.INSTRUMENT_METADATA.get(symbol)
        if not metadata:
            self.stdout.write(self.style.ERROR(
                f'No metadata defined for symbol "{symbol}"\n'
                f'Available symbols: {", ".join(self.INSTRUMENT_METADATA.keys())}'
            ))
            return

        instruments = TradingInstrument.objects.filter(
            symbol__in=[symbol, f'/{symbol}', symbol.lstrip('/')]
        )

        if not instruments.exists():
            self.stdout.write(self.style.ERROR(
                f'Instrument "{symbol}" not found in database'
            ))
            return

        for instrument in instruments:
            self._apply_metadata(instrument, metadata, dry_run)

    def update_all_instruments(self, dry_run):
        """Update metadata for all instruments."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Syncing metadata for all futures instruments...\n'
        ))

        updated_count = 0
        not_found = []

        for symbol, metadata in self.INSTRUMENT_METADATA.items():
            instruments = TradingInstrument.objects.filter(
                symbol__in=[symbol, f'/{symbol}']
            )

            if not instruments.exists():
                not_found.append(symbol)
                continue

            for instrument in instruments:
                if self._apply_metadata(instrument, metadata, dry_run):
                    updated_count += 1

        # Summary
        self.stdout.write('\n' + '='*70)
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
                f'\nNot found in database: {", ".join(not_found)}'
            ))

        # Show current state
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Current metadata:'))
        self.stdout.write(
            f'{"Symbol":<10} {"Precision":<12} {"Tick Value":<15} {"Margin":<15}'
        )
        self.stdout.write('-' * 70)

        all_instruments = TradingInstrument.objects.filter(is_active=True).order_by('symbol')
        for inst in all_instruments:
            precision = f'{inst.display_precision} decimals'
            tick = f'${inst.tick_value}' if inst.tick_value else 'Not set'
            margin = f'${inst.margin_requirement:,.2f}' if inst.margin_requirement else 'Not set'
            self.stdout.write(f'{inst.symbol:<10} {precision:<12} {tick:<15} {margin:<15}')

    def _apply_metadata(self, instrument, metadata, dry_run):
        """Apply metadata to an instrument and return True if changes were made."""
        changes = []

        # Check what needs updating
        if instrument.display_precision != metadata['display_precision']:
            changes.append(
                f"precision: {instrument.display_precision} → {metadata['display_precision']}"
            )

        if instrument.tick_value != metadata['tick_value']:
            old_tick = f'${instrument.tick_value}' if instrument.tick_value else 'None'
            changes.append(f"tick: {old_tick} → ${metadata['tick_value']}")

        if instrument.margin_requirement != metadata['margin_requirement']:
            old_margin = f'${instrument.margin_requirement:,.2f}' if instrument.margin_requirement else 'None'
            changes.append(f"margin: {old_margin} → ${metadata['margin_requirement']:,.2f}")

        if not changes:
            self.stdout.write(f'  {instrument.symbol}: ✓ Already up to date')
            return False

        # Apply changes
        change_summary = ', '.join(changes)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'  {instrument.symbol}: Would update ({change_summary})'
            ))
        else:
            instrument.display_precision = metadata['display_precision']
            instrument.tick_value = metadata['tick_value']
            instrument.margin_requirement = metadata['margin_requirement']
            instrument.save()
            self.stdout.write(self.style.SUCCESS(
                f'  {instrument.symbol}: Updated ({change_summary})'
            ))

        return True
