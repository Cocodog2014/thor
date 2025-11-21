import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from GlobalMarkets.models import Market

print('=== CURRENT MARKET STATUS ===')
print(f'{"Market":<20} | {"DB Status":<10} | {"Actually Open":<15} | {"Match?":<8}')
print('-' * 70)

markets = Market.objects.filter(is_active=True).order_by('country')

for m in markets:
    is_open_now = m.is_market_open_now()
    db_status = m.status
    match = '✓' if (db_status == 'OPEN' and is_open_now) or (db_status == 'CLOSED' and not is_open_now) else '✗ MISMATCH'
    
    print(f'{m.country:<20} | {db_status:<10} | {str(is_open_now):<15} | {match:<8}')

print('\n=== KEY INSIGHT ===')
print('The DB "status" field is static. Frontend calculates OPEN/CLOSED in real-time.')
print('For market open capture to work, we need to UPDATE the DB status when markets open.')
