"""
Test script for MarketOpen models
Run with: python manage.py shell < scripts/test_market_open_models.py
Or: python scripts/test_market_open_models.py (if Django setup is configured)
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot
from decimal import Decimal
from django.utils import timezone

print("=" * 60)
print("Testing MarketOpen Models")
print("=" * 60)

# Test 1: Create a MarketOpenSession
print("\n1. Creating MarketOpenSession...")
try:
    session = MarketOpenSession.objects.create(
        session_number=1,
        year=2025,
        month=10,
        date=26,
        day="Saturday",
        country="Japan",
        ym_ask=Decimal("47388.00"),
        ym_bid=Decimal("47380.00"),
        ym_last=Decimal("47387.00"),
        ym_entry_price=Decimal("47388.00"),  # Buying at ask
        ym_high_dynamic=Decimal("47408.00"),  # +20 points
        ym_low_dynamic=Decimal("47368.00"),   # -20 points
        total_signal="BUY",
        fw_weight=Decimal("5.0"),
    )
    print(f"✅ Created session: {session}")
except Exception as e:
    print(f"❌ Error creating session: {e}")
    sys.exit(1)

# Test 2: Create FutureSnapshot for YM
print("\n2. Creating FutureSnapshot for YM...")
try:
    ym_snapshot = FutureSnapshot.objects.create(
        session=session,
        symbol="YM",
        last_price=Decimal("47387.00"),
        change=Decimal("-9.00"),
        change_percent=Decimal("-0.0002"),
        bid=Decimal("47380.00"),
        bid_size=2,
        ask=Decimal("47388.00"),
        ask_size=2,
        volume=150000,
        vwap=Decimal("47385.50"),
        spread=Decimal("8.00"),
        close=Decimal("47396.00"),
        entry_price=Decimal("47388.00"),
        high_dynamic=Decimal("47408.00"),
        low_dynamic=Decimal("47368.00"),
    )
    print(f"✅ Created YM snapshot: {ym_snapshot}")
except Exception as e:
    print(f"❌ Error creating YM snapshot: {e}")
    sys.exit(1)

# Test 3: Create FutureSnapshot for TOTAL
print("\n3. Creating FutureSnapshot for TOTAL...")
try:
    total_snapshot = FutureSnapshot.objects.create(
        session=session,
        symbol="TOTAL",
        weighted_average=Decimal("-0.109"),
        signal="HOLD",
        weight=-3,
        sum_weighted=Decimal("13.02"),
        instrument_count=11,
        status="LIVE TOTAL",
    )
    print(f"✅ Created TOTAL snapshot: {total_snapshot}")
except Exception as e:
    print(f"❌ Error creating TOTAL snapshot: {e}")
    sys.exit(1)

# Test 4: Query and verify
print("\n4. Querying data...")
try:
    sessions = MarketOpenSession.objects.all()
    print(f"✅ Total sessions: {sessions.count()}")
    
    futures = FutureSnapshot.objects.filter(session=session)
    print(f"✅ Futures snapshots for session: {futures.count()}")
    
    for future in futures:
        print(f"   - {future.symbol}: {future}")
except Exception as e:
    print(f"❌ Error querying: {e}")
    sys.exit(1)

# Test 5: Test relationships
print("\n5. Testing relationships...")
try:
    print(f"✅ Session futures: {session.futures.count()}")
    for future in session.futures.all():
        print(f"   - {future.symbol}")
except Exception as e:
    print(f"❌ Error testing relationships: {e}")
    sys.exit(1)

# Test 6: Update outcome
print("\n6. Testing outcome update...")
try:
    session.fw_nwdw = "WORKED"
    session.fw_exit_value = Decimal("47408.00")
    session.save()
    print(f"✅ Updated session outcome: {session.fw_nwdw}")
except Exception as e:
    print(f"❌ Error updating outcome: {e}")
    sys.exit(1)

# Cleanup
print("\n7. Cleanup (deleting test data)...")
try:
    session.delete()
    print("✅ Test data deleted")
except Exception as e:
    print(f"❌ Error cleaning up: {e}")

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
