"""
Seed Market Open Sessions with synthetic data for frontend testing.

Usage:
    python manage.py seed_market_open_sessions            # Seed all control markets
    python manage.py seed_market_open_sessions --country USA
    python manage.py seed_market_open_sessions --clear    # Clear today's rows for target markets before seeding
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random

from FutureTrading.models.MarketSession import MarketSession


CONTROL_COUNTRIES = [
    'Japan', 'China', 'India', 'Germany', 'United Kingdom',
    'Pre_USA', 'USA', 'Canada', 'Mexico'
]

FUTURES_SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
SIGNALS = ['BUY', 'HOLD', 'SELL', 'STRONG_BUY', 'STRONG_SELL']


class Command(BaseCommand):
    help = 'Seed synthetic MarketOpenSession rows for testing the frontend (single-table design)'

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, help='Single country to seed (default: all control markets)')
        parser.add_argument('--clear', action='store_true', help="Clear today's rows for selected markets before seeding")
        parser.add_argument('--seed', type=int, help='Random seed for reproducibility')

    def handle(self, *args, **options):
        if options.get('seed') is not None:
            random.seed(int(options['seed']))

        countries = [options['country']] if options.get('country') else CONTROL_COUNTRIES

        now = timezone.now()
        time_info = {
            'year': now.year,
            'month': now.month,
            'date': now.day,
            'day': now.strftime('%A')
        }

        # Determine next session number
        last = MarketSession.objects.order_by('-session_number').first()
        session_number = (last.session_number + 1) if last else 1

        if options.get('clear'):
            for c in countries:
                MarketSession.objects.filter(
                    country=c,
                    year=time_info['year'],
                    month=time_info['month'],
                    date=time_info['date']
                ).delete()
            self.stdout.write(self.style.WARNING('Cleared existing rows for selected markets (today).'))

        created = 0
        for country in countries:
            # Create 11 futures rows
            for idx, symbol in enumerate(FUTURES_SYMBOLS):
                base = Decimal(str(random.uniform(50, 5000))).quantize(Decimal('0.01'))
                chg = Decimal(str(random.uniform(-2.5, 2.5))).quantize(Decimal('0.01'))
                bid = (base - Decimal('0.05')).quantize(Decimal('0.01'))
                ask = (base + Decimal('0.05')).quantize(Decimal('0.01'))
                sig = random.choice(SIGNALS)

                data = {
                    'session_number': session_number,
                    'year': time_info['year'],
                    'month': time_info['month'],
                    'date': time_info['date'],
                    'day': time_info['day'],
                    'country': country,
                    'future': symbol,
                    'captured_at': timezone.now(),
                    'wndw': 'PENDING',
                    'last_price': base,
                    'change': chg,
                    'change_percent': (chg / base * 100).quantize(Decimal('0.01')),
                    'reference_bid': bid,
                    'bid_size': random.randint(1, 10),
                    'reference_ask': ask,
                    'ask_size': random.randint(1, 10),
                    'volume': random.randint(1000, 2_000_000),
                    'vwap': base,
                    'spread': (ask - bid).quantize(Decimal('0.0001')),
                    'reference_open': (base - chg).quantize(Decimal('0.01')),
                    'reference_close': (base - chg).quantize(Decimal('0.01')),
                    'day_24h_low': (base - Decimal('1.00')).quantize(Decimal('0.01')),
                    'day_24h_high': (base + Decimal('1.00')).quantize(Decimal('0.01')),
                    'range_high_low': Decimal('2.00'),
                    'range_percent': Decimal('0.05'),
                    'week_52_low': (base * Decimal('0.7')).quantize(Decimal('0.01')),
                    'week_52_high': (base * Decimal('1.3')).quantize(Decimal('0.01')),
                    'bhs': sig,
                    'weight': random.randint(0, 5),
                    'study_fw': 'HBS',
                    'outcome': 'PENDING',
                    'fw_nwdw': 'PENDING',
                }

                # Entry/targets
                if sig not in ['HOLD', None, '']:
                    if sig in ['BUY', 'STRONG_BUY']:
                        data['entry_price'] = data['reference_ask']
                        data['target_high'] = data['entry_price'] + Decimal('20')
                        data['target_low'] = data['entry_price'] - Decimal('20')
                    elif sig in ['SELL', 'STRONG_SELL']:
                        data['entry_price'] = data['reference_bid']
                        data['target_high'] = data['entry_price'] + Decimal('20')
                        data['target_low'] = data['entry_price'] - Decimal('20')

                MarketSession.objects.create(**data)
                created += 1

            # TOTAL row
            total = {
                'session_number': session_number,
                'year': time_info['year'],
                'month': time_info['month'],
                'date': time_info['date'],
                'day': time_info['day'],
                'country': country,
                'future': 'TOTAL',
                'captured_at': timezone.now(),
                'wndw': 'NEUTRAL',
                'weighted_average': Decimal(str(random.uniform(-1.0, 1.0))).quantize(Decimal('0.0001')),
                'sum_weighted': Decimal(str(random.uniform(-5.0, 5.0))).quantize(Decimal('0.0001')),
                'instrument_count': len(FUTURES_SYMBOLS),
                'bhs': random.choice(SIGNALS),
                'weight': random.randint(5, 25),
                'status': 'LIVE TOTAL',
                'study_fw': 'TOTAL',
                'outcome': 'NEUTRAL',
                'fw_nwdw': 'NEUTRAL',
            }
            MarketSession.objects.create(**total)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} MarketOpenSession rows (Session #{session_number})."))
