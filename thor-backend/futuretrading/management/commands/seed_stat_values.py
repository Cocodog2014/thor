from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from futuretrading.models import TradingInstrument, SignalStatValue, ContractWeight, InstrumentCategory


class Command(BaseCommand):
    help = 'Seed statistical values for futures instruments'
    
    # Statistical values mapping from your handoff note
    STAT_VALUES = {
        'YM': {'STRONG_BUY': 60, 'BUY': 10, 'HOLD': 0, 'SELL': -10, 'STRONG_SELL': -60},
        'ES': {'STRONG_BUY': 6, 'BUY': 1, 'HOLD': 0, 'SELL': -1, 'STRONG_SELL': -6},
        'NQ': {'STRONG_BUY': 15, 'BUY': 2.5, 'HOLD': 0, 'SELL': -2.5, 'STRONG_SELL': -15},
        'RTY': {'STRONG_BUY': 15, 'BUY': 2.5, 'HOLD': 0, 'SELL': -2.5, 'STRONG_SELL': -15},
        'CL': {'STRONG_BUY': 0.3, 'BUY': 0.05, 'HOLD': 0, 'SELL': -0.05, 'STRONG_SELL': -0.3},
        'SI': {'STRONG_BUY': 0.06, 'BUY': 0.01, 'HOLD': 0, 'SELL': -0.01, 'STRONG_SELL': -0.06},
        'HG': {'STRONG_BUY': 0.012, 'BUY': 0.002, 'HOLD': 0, 'SELL': -0.002, 'STRONG_SELL': -0.012},
        'GC': {'STRONG_BUY': 3, 'BUY': 0.5, 'HOLD': 0, 'SELL': -0.5, 'STRONG_SELL': -3},
        'VX': {'STRONG_BUY': 0.10, 'BUY': 0.05, 'HOLD': 0, 'SELL': -0.05, 'STRONG_SELL': -0.10},
        'DX': {'STRONG_BUY': 30, 'BUY': 5, 'HOLD': 0, 'SELL': -5, 'STRONG_SELL': -30},
        'ZB': {'STRONG_BUY': 30, 'BUY': 5, 'HOLD': 0, 'SELL': -5, 'STRONG_SELL': -30},  # 30Y Treasury (kept)
    }
    
    # Default contract weights (all equal for now) - removed ZN
    DEFAULT_WEIGHTS = {
        'YM': 1.0, 'ES': 1.5, 'NQ': 1.2, 'RTY': 1.0, 'CL': 1.3, 'SI': 1.0,
        'HG': 1.0, 'GC': 1.4, 'VX': 0.8, 'DX': 1.0, 'ZB': 1.1
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-instruments',
            action='store_true',
            help='Create missing instruments if they don\'t exist',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing statistical values',
        )
    
    def handle(self, *args, **options):
        with transaction.atomic():
            self.create_futures_category()
            
            if options['create_instruments']:
                self.create_missing_instruments()
            
            self.seed_stat_values(options['overwrite'])
            self.seed_contract_weights(options['overwrite'])
    
    def create_futures_category(self):
        """Ensure futures category exists"""
        category, created = InstrumentCategory.objects.get_or_create(
            name='futures',
            defaults={
                'display_name': 'Futures Contracts',
                'description': 'Futures trading instruments',
                'color_primary': '#FF6B35',
                'color_secondary': '#FF8A65',
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created futures category: {category}')
            )
        return category
    
    def create_missing_instruments(self):
        """Create any missing futures instruments"""
        futures_category = InstrumentCategory.objects.get(name='futures')
        
        # Instrument details
        instruments_data = {
            'YM': {'name': 'Dow Jones Mini Futures', 'exchange': 'CBOT'},
            'ES': {'name': 'S&P 500 Mini Futures', 'exchange': 'CME'},
            'NQ': {'name': 'Nasdaq 100 Mini Futures', 'exchange': 'CME'},
            'RTY': {'name': 'Russell 2000 Mini Futures', 'exchange': 'CME'},
            'CL': {'name': 'Crude Oil Futures', 'exchange': 'NYMEX'},
            'SI': {'name': 'Silver Futures', 'exchange': 'COMEX'},
            'HG': {'name': 'Copper Futures', 'exchange': 'COMEX'},
            'GC': {'name': 'Gold Futures', 'exchange': 'COMEX'},
            'VX': {'name': 'VIX Futures', 'exchange': 'CFE'},
            'DX': {'name': 'US Dollar Index Futures', 'exchange': 'ICE'},
            'ZB': {'name': '30-Year Treasury Bond Futures', 'exchange': 'CBOT'},
        }
        
        for symbol, data in instruments_data.items():
            # Try with and without forward slash
            symbols_to_try = [symbol, f'/{symbol}']
            existing = TradingInstrument.objects.filter(symbol__in=symbols_to_try).first()
            
            if not existing:
                instrument = TradingInstrument.objects.create(
                    symbol=f'/{symbol}',  # Use forward slash convention
                    name=data['name'],
                    exchange=data['exchange'],
                    category=futures_category,
                    is_active=True,
                    is_watchlist=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created instrument: {instrument}')
                )
    
    def seed_stat_values(self, overwrite=False):
        """Seed statistical values for all instruments"""
        created_count = 0
        updated_count = 0
        
        for symbol_base, values in self.STAT_VALUES.items():
            # Try to find instrument with or without forward slash
            symbols_to_try = [symbol_base, f'/{symbol_base}']
            instrument = TradingInstrument.objects.filter(symbol__in=symbols_to_try).first()
            
            if not instrument:
                self.stdout.write(
                    self.style.WARNING(f'Instrument not found for symbol: {symbol_base} (tried {symbols_to_try})')
                )
                continue
            
            for signal, value in values.items():
                stat_value, created = SignalStatValue.objects.get_or_create(
                    instrument=instrument,
                    signal=signal,
                    defaults={'value': Decimal(str(value))}
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  Created: {instrument.symbol} {signal} = {value}')
                elif overwrite:
                    stat_value.value = Decimal(str(value))
                    stat_value.save()
                    updated_count += 1
                    self.stdout.write(f'  Updated: {instrument.symbol} {signal} = {value}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Stat values - Created: {created_count}, Updated: {updated_count}')
        )
    
    def seed_contract_weights(self, overwrite=False):
        """Seed contract weights for all instruments"""
        created_count = 0
        updated_count = 0
        
        for symbol_base, weight in self.DEFAULT_WEIGHTS.items():
            # Try to find instrument with or without forward slash
            symbols_to_try = [symbol_base, f'/{symbol_base}']
            instrument = TradingInstrument.objects.filter(symbol__in=symbols_to_try).first()
            
            if not instrument:
                continue
            
            contract_weight, created = ContractWeight.objects.get_or_create(
                instrument=instrument,
                defaults={'weight': Decimal(str(weight))}
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  Created weight: {instrument.symbol} = {weight}')
            elif overwrite:
                contract_weight.weight = Decimal(str(weight))
                contract_weight.save()
                updated_count += 1
                self.stdout.write(f'  Updated weight: {instrument.symbol} = {weight}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Contract weights - Created: {created_count}, Updated: {updated_count}')
        )