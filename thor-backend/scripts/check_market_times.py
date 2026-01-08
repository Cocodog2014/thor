"""Check market times for Frankfurt and London"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from GlobalMarkets.models.market_clock import Market

markets = Market.objects.filter(country__in=['Germany', 'United Kingdom']).order_by('country')

for m in markets:
    print(f"{m.country}: {m.timezone_name}")
    print(f"  Open: {m.market_open_time}")
    print(f"  Close: {m.market_close_time}")
    print()
