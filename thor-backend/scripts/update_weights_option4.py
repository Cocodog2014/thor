"""
Update contract weights for better Bull/Bear balance
Option 4: Hybrid Approach
"""
import os
import sys
sys.path.insert(0, r'A:\Thor\thor-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')

import django
django.setup()

from FutureTrading.models import ContractWeight, TradingInstrument
from decimal import Decimal

# New weights - Option 4 (Hybrid)
new_weights = {
    '/YM': '55.000000',    # Down from 60 (still most important)
    '/ES': '6.000000',     # Keep same
    '/NQ': '15.000000',    # Keep same
    '/RTY': '15.000000',   # Keep same (was 1, but shows 15 in DB)
    '/CL': '0.300000',     # Keep same
    '/SI': '0.060000',     # Keep same
    '/HG': '0.012000',     # Keep same
    '/GC': '4.000000',     # Up from 3 (important safe haven)
    '/VX': '0.300000',     # Up from 0.1 (fear gauge should matter more)
    '/DX': '35.000000',    # Up from 30 (dollar strength critical)
    '/ZB': '35.000000',    # Up from 30 (bond yields critical)
}

print("Updating Contract Weights - Option 4 (Hybrid Approach)")
print("=" * 60)

for symbol, weight in new_weights.items():
    try:
        instrument = TradingInstrument.objects.get(symbol=symbol)
        contract_weight, created = ContractWeight.objects.get_or_create(
            instrument=instrument,
            defaults={'weight': weight}
        )
        
        old_weight = contract_weight.weight
        contract_weight.weight = Decimal(weight)
        contract_weight.save()
        
        status = "CREATED" if created else f"UPDATED (was {old_weight})"
        print(f"✓ {symbol:6s}: {weight:12s} [{status}]")
        
    except TradingInstrument.DoesNotExist:
        print(f"✗ {symbol}: Instrument not found in database")
    except Exception as e:
        print(f"✗ {symbol}: Error - {e}")

print("\n" + "=" * 60)
print("Summary of Changes:")
print("-" * 60)

# Calculate new totals
bull_weights = [55, 6, 15, 15, 0.3, 0.06, 0.012]
bear_weights = [4, 0.3, 35, 35]

bull_total = sum(bull_weights)
bear_total = sum(bear_weights)
total = bull_total + bear_total

print(f"\nBULL INSTRUMENTS:")
print(f"  YM:  55    (was 60)")
print(f"  ES:  6     (no change)")
print(f"  NQ:  15    (no change)")
print(f"  RTY: 15    (no change)")
print(f"  CL:  0.3   (no change)")
print(f"  SI:  0.06  (no change)")
print(f"  HG:  0.012 (no change)")
print(f"  TOTAL: {bull_total:.3f}")

print(f"\nBEAR INSTRUMENTS:")
print(f"  GC:  4     (was 3)")
print(f"  VX:  0.3   (was 0.1)")
print(f"  DX:  35    (was 30)")
print(f"  ZB:  35    (was 30)")
print(f"  TOTAL: {bear_total:.3f}")

print(f"\nBALANCE:")
print(f"  Bull/Bear Ratio: {bull_total/bear_total:.2f}:1")
print(f"  Bear Weight %: {(bear_total/total)*100:.1f}%")
print(f"  Total Weight: {total:.3f}")

print("\n✓ Weight adjustments complete!")
