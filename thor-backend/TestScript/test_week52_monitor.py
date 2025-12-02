"""Quick test script to verify Week 52 monitor works."""

import os
import sys
import django

# Setup Django
sys.path.insert(0, 'a:\\Thor\\thor-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

print("=" * 60)
print("Testing Week 52 Monitor")
print("=" * 60)

# Import and test
from FutureTrading.services.Week52Supervisor import start_52w_monitor

print("\n1. Attempting to start monitor...")
start_52w_monitor()

print("\n2. Checking if monitor thread is running...")
from FutureTrading.services.Week52Supervisor import get_52w_monitor
monitor = get_52w_monitor()
print(f"   Monitor running: {monitor._running}")
print(f"   Monitor thread: {monitor._thread}")

print("\n3. Checking Redis for data...")
from LiveData.shared.redis_client import live_data_redis
test_symbols = ['YM', 'ES', 'RT', '30YRBOND']
for sym in test_symbols:
    quote = live_data_redis.get_latest_quote(sym)
    if quote:
        print(f"   ✓ {sym}: last={quote.get('last')}")
    else:
        print(f"   ✗ {sym}: No data")

print("\n4. Checking database for 52w stats...")
from FutureTrading.models.extremes import Rolling52WeekStats
stats = Rolling52WeekStats.objects.all()
print(f"   Found {stats.count()} records")
for s in stats[:3]:
    print(f"   - {s.symbol}: H={s.high_52w} L={s.low_52w}")

print("\n" + "=" * 60)
print("Test complete. Monitor should be running in background.")
print("=" * 60)
