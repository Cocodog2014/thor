import os
import sys
import django

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis

# Get latest session and check each future
latest = MarketSession.objects.order_by('-captured_at').first()
if not latest:
    print("No sessions found")
    sys.exit(0)

futures = MarketSession.objects.filter(
    session_number=latest.session_number,
    country=latest.country
).values_list('future', flat=True).distinct()

print("Testing Redis key availability for each future:")
print("=" * 70)

for future in sorted(futures):
    if not future:
        continue
    
    # Test with slash
    with_slash = f'/{future}'
    data_slash = live_data_redis.get_latest_quote(with_slash)
    
    # Test without slash
    no_slash = future
    data_no_slash = live_data_redis.get_latest_quote(no_slash)
    
    status = []
    if data_slash and data_slash.get('bid'):
        status.append(f"✓ {with_slash}")
    else:
        status.append(f"✗ {with_slash}")
    
    if data_no_slash and data_no_slash.get('bid'):
        status.append(f"✓ {no_slash}")
    else:
        status.append(f"✗ {no_slash}")
    
    print(f"{future:10} → {' | '.join(status)}")
