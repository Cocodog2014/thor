"""Test script to verify target capture fix"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.TargetHighLow import compute_targets_for_symbol
from decimal import Decimal

print("Testing target capture logic...\n")

enriched, composite = get_enriched_quotes_with_composite()

print(f"Composite signal: {composite.get('composite_signal')}\n")

for row in enriched[:5]:
    symbol = row['instrument']['symbol']
    ext = row.get('extended_data', {})
    individual_signal = (ext.get('signal') or '').upper()
    ask = row.get('ask')
    bid = row.get('bid')
    
    print(f"{symbol}: bhs={individual_signal}, ask={ask}, bid={bid}")
    
    if individual_signal and individual_signal not in ['HOLD', '']:
        if individual_signal in ['BUY', 'STRONG_BUY']:
            entry = Decimal(str(ask)) if ask else None
        elif individual_signal in ['SELL', 'STRONG_SELL']:
            entry = Decimal(str(bid)) if bid else None
        else:
            entry = None
            
        if entry:
            high, low = compute_targets_for_symbol(symbol, entry)
            print(f"  → entry={entry}, target_high={high}, target_low={low}")
        else:
            print(f"  → No entry price available")
    print()
