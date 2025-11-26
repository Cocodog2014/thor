"""
One-time script to mark the 9 control markets in the database.
Run this once to set is_control_market=True and weights.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from GlobalMarkets.models import Market
from decimal import Decimal

CONTROL_MARKETS = {
    'Japan': 0.25,
    'China': 0.10,
    'India': 0.05,
    'Germany': 0.20,
    'United Kingdom': 0.05,
    'Pre_USA': 0.05,
    'USA': 0.25,
    'Canada': 0.03,
    'Mexico': 0.02,
}

print('=== Setting Control Markets ===\n')

# First, unmark all markets
Market.objects.all().update(is_control_market=False, weight=Decimal('0.00'))
print('✓ Cleared all control market flags')

# Then mark the 9 control markets
for country, weight in CONTROL_MARKETS.items():
    market = Market.objects.filter(country=country).first()
    if market:
        market.is_control_market = True
        market.weight = Decimal(str(weight))
        market.save()
        print(f'✓ {country:20} → Control market (weight: {weight*100}%)')
    else:
        print(f'✗ {country:20} → NOT FOUND in database!')

print(f'\n✅ Done! {Market.objects.filter(is_control_market=True).count()} control markets set')
