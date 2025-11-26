import os
import sys
import django

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from LiveData.shared.redis_client import live_data_redis

# Test different key patterns
test_keys = ['/YM', 'YM', '/ES', 'ES', '$DXY', 'DX']

print("Testing Redis keys:")
print("=" * 60)
for key in test_keys:
    data = live_data_redis.get_latest_quote(key)
    if data:
        print(f"✓ {key:10} → HAS DATA (bid={data.get('bid')}, ask={data.get('ask')})")
    else:
        print(f"✗ {key:10} → NO DATA")
