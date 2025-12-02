#!/usr/bin/env python
"""
Populate Futures Trading data from the statistical values table.
This creates instruments, categories, and all weight/stat values.

Run: python manage.py shell < populate_futures_data.py
"""

import django
import os
import sys

# Setup Django - add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from decimal import Decimal
from ThorTrading.models import (
    InstrumentCategory, TradingInstrument, SignalWeight,
    ContractWeight, SignalStatValue
)

# Data extracted from the statistical values image
INSTRUMENTS = {
    '/YM': {
        'name': 'E-mini Dow',
        'exchange': 'CBOT',
        'contract_weight': Decimal('60'),
        'stats': {
            'STRONG_BUY': Decimal('60'),
            'BUY': Decimal('10'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-10'),
            'STRONG_SELL': Decimal('-60'),
        }
    },
    '/ES': {
        'name': 'E-mini S&P 500',
        'exchange': 'CME',
        'contract_weight': Decimal('6'),
        'stats': {
            'STRONG_BUY': Decimal('6'),
            'BUY': Decimal('1'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-1'),
            'STRONG_SELL': Decimal('-6'),
        }
    },
    '/NQ': {
        'name': 'E-mini Nasdaq',
        'exchange': 'CME',
        'contract_weight': Decimal('15'),
        'stats': {
            'STRONG_BUY': Decimal('15'),
            'BUY': Decimal('2.5'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-2.5'),
            'STRONG_SELL': Decimal('-15'),
        }
    },
    '/RTY': {
        'name': 'E-mini Russell 2000',
        'exchange': 'CME',
        'contract_weight': Decimal('15'),
        'stats': {
            'STRONG_BUY': Decimal('15'),
            'BUY': Decimal('2.5'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-2.5'),
            'STRONG_SELL': Decimal('-15'),
        }
    },
    '/CL': {
        'name': 'Crude Oil',
        'exchange': 'NYMEX',
        'contract_weight': Decimal('0.3'),
        'stats': {
            'STRONG_BUY': Decimal('0.3'),
            'BUY': Decimal('0.05'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-0.05'),
            'STRONG_SELL': Decimal('-0.3'),
        }
    },
    '/SI': {
        'name': 'Silver',
        'exchange': 'COMEX',
        'contract_weight': Decimal('0.06'),
        'stats': {
            'STRONG_BUY': Decimal('0.06'),
            'BUY': Decimal('0.01'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-0.01'),
            'STRONG_SELL': Decimal('-0.06'),
        }
    },
    '/HG': {
        'name': 'Copper',
        'exchange': 'COMEX',
        'contract_weight': Decimal('0.012'),
        'stats': {
            'STRONG_BUY': Decimal('0.012'),
            'BUY': Decimal('0.002'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-0.002'),
            'STRONG_SELL': Decimal('-0.012'),
        }
    },
    '/GC': {
        'name': 'Gold',
        'exchange': 'COMEX',
        'contract_weight': Decimal('3'),
        'stats': {
            'STRONG_BUY': Decimal('3'),
            'BUY': Decimal('0.5'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-0.5'),
            'STRONG_SELL': Decimal('-3'),
        }
    },
    '/VX': {
        'name': 'VIX',
        'exchange': 'CFE',
        'contract_weight': Decimal('0.1'),
        'stats': {
            'STRONG_BUY': Decimal('0.1'),
            'BUY': Decimal('0.05'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-0.05'),
            'STRONG_SELL': Decimal('-0.1'),
        }
    },
    '/DX': {
        'name': 'US Dollar Index',
        'exchange': 'ICE',
        'contract_weight': Decimal('30'),
        'stats': {
            'STRONG_BUY': Decimal('30'),
            'BUY': Decimal('5'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-5'),
            'STRONG_SELL': Decimal('-30'),
        }
    },
    '/ZB': {
        'name': '30-Year T-Bond',
        'exchange': 'CBOT',
        'contract_weight': Decimal('30'),
        'stats': {
            'STRONG_BUY': Decimal('30'),
            'BUY': Decimal('5'),
            'HOLD': Decimal('0'),
            'SELL': Decimal('-5'),
            'STRONG_SELL': Decimal('-30'),
        }
    },
}

def main():
    print("="*70)
    print("POPULATING FUTURES TRADING DATA")
    print("="*70)
    
    # 1. Create category
    print("\n[1/4] Creating Futures category...")
    category, created = InstrumentCategory.objects.get_or_create(
        name='futures',
        defaults={
            'display_name': 'Futures Contracts',
            'description': 'CME, CBOT, NYMEX, COMEX futures',
            'is_active': True,
            'sort_order': 1,
        }
    )
    print(f"  {'✓ Created' if created else '→ Using existing'}: {category.display_name}")
    
    # 2. Create signal weights
    print("\n[2/4] Creating Signal Weights...")
    for signal, weight in [('STRONG_BUY', 2), ('BUY', 1), ('HOLD', 0), ('SELL', -1), ('STRONG_SELL', -2)]:
        obj, created = SignalWeight.objects.update_or_create(
            signal=signal,
            defaults={'weight': weight}
        )
        print(f"  {'✓' if created else '→'} {signal}: {weight}")
    
    # 3. Create instruments with contract weights
    print("\n[3/4] Creating Trading Instruments & Contract Weights...")
    for symbol, data in INSTRUMENTS.items():
        instrument, created = TradingInstrument.objects.update_or_create(
            symbol=symbol,
            defaults={
                'name': data['name'],
                'category': category,
                'exchange': data['exchange'],
                'is_active': True,
                'is_watchlist': True,
                'display_precision': 2,
            }
        )
        print(f"  {'✓' if created else '→'} {symbol} - {data['name']}")
        
        # Contract weight
        cw, cw_created = ContractWeight.objects.update_or_create(
            instrument=instrument,
            defaults={'weight': data['contract_weight']}
        )
        print(f"      Weight: {data['contract_weight']}")
    
    # 4. Create signal stat values
    print("\n[4/4] Creating Signal Statistical Values...")
    total_stats = 0
    for symbol, data in INSTRUMENTS.items():
        instrument = TradingInstrument.objects.get(symbol=symbol)
        for signal, value in data['stats'].items():
            obj, created = SignalStatValue.objects.update_or_create(
                instrument=instrument,
                signal=signal,
                defaults={'value': value}
            )
            if created:
                total_stats += 1
        print(f"  ✓ {symbol}: 5 signal thresholds")
    
    # Verify
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    print(f"✓ Instruments: {TradingInstrument.objects.count()}")
    print(f"✓ Contract Weights: {ContractWeight.objects.count()}")
    print(f"✓ Signal Weights: {SignalWeight.objects.count()}")
    print(f"✓ Signal Stat Values: {SignalStatValue.objects.count()}")
    print("\n✓ ALL DATA POPULATED SUCCESSFULLY!")
    print("\nNext: Restart Django server and refresh your dashboard.")
    print("="*70)

if __name__ == '__main__':
    main()

