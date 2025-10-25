"""
Management command to populate tick_value and margin_requirement for futures instruments.

Usage:
    python manage.py populate_trading_values
    python manage.py populate_trading_values --symbol YM
"""

from django.core.management.base import BaseCommand
from FutureTrading.models import TradingInstrument
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate tick_value and margin_requirement for trading instruments'

    # Standard trading values for common futures
    TRADING_VALUES = {
        'YM': {
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('17000.00'),
        },
        'ES': {
            'tick_value': Decimal('12.50'),
            'margin_requirement': Decimal('13000.00'),
        },
        'NQ': {
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('16000.00'),
        },
        'RTY': {
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('7500.00'),
        },
        'RT': {
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('7500.00'),
        },
        'CL': {
            'tick_value': Decimal('10.00'),
            'margin_requirement': Decimal('8000.00'),
        },
        'GC': {
            'tick_value': Decimal('10.00'),
            'margin_requirement': Decimal('11000.00'),
        },
        'SI': {
            'tick_value': Decimal('25.00'),
            'margin_requirement': Decimal('14000.00'),
        },
        'HG': {
            'tick_value': Decimal('12.50'),
            'margin_requirement': Decimal('4000.00'),
        },
        'VX': {
            'tick_value': Decimal('50.00'),
            'margin_requirement': Decimal('6000.00'),
        },
        'DX': {
            'tick_value': Decimal('5.00'),
            'margin_requirement': Decimal('2500.00'),
        },
        'ZB': {
            'tick_value': Decimal('31.25'),
            'margin_requirement': Decimal('5000.00'),
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Symbol to update (e.g., YM, ES, NQ)',
        )

    def handle(self, *args, **options):
        symbol = options.get('symbol')

        if symbol:
            self.update_single_instrument(symbol)
        else:
            self.update_all_instruments()

    def update_single_instrument(self, symbol):
        """Update a single instrument's trading values."""
        values = self.TRADING_VALUES.get(symbol)
        if not values:
            self.stdout.write(self.style.ERROR(
                f'No trading values defined for symbol "{symbol}"'
            ))
            return

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
            instrument.tick_value = values['tick_value']
            instrument.margin_requirement = values['margin_requirement']
            instrument.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Updated {instrument.symbol}: '
                f'Tick=${values["tick_value"]}, Margin=${values["margin_requirement"]}'
            ))

    def update_all_instruments(self):
        """Update all instruments with standard trading values."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Updating trading values for all futures instruments...\n'
        ))

        updated_count = 0
        not_found = []

        for symbol, values in self.TRADING_VALUES.items():
            # Try with and without leading slash
            instruments = TradingInstrument.objects.filter(
                symbol__in=[symbol, f'/{symbol}']
            )

            if not instruments.exists():
                not_found.append(symbol)
                continue

            for instrument in instruments:
                instrument.tick_value = values['tick_value']
                instrument.margin_requirement = values['margin_requirement']
                instrument.save()
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Updated {instrument.symbol}: '
                    f'Tick=${values["tick_value"]}, Margin=${values["margin_requirement"]}'
                ))
                updated_count += 1

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(
            f'✓ Updated {updated_count} instrument(s)'
        ))

        if not_found:
            self.stdout.write(self.style.WARNING(
                f'\nInstruments not found in database: {", ".join(not_found)}'
            ))

        # Show current settings
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Current trading values:'))
        all_instruments = TradingInstrument.objects.filter(is_active=True).order_by('symbol')
        for inst in all_instruments:
            tick_val = f'${inst.tick_value}' if inst.tick_value else 'Not set'
            margin_val = f'${inst.margin_requirement:,.2f}' if inst.margin_requirement else 'Not set'
            self.stdout.write(f'  {inst.symbol:10s} → Tick: {tick_val:10s} Margin: {margin_val}')
