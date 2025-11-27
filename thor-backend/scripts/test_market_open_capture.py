"""
Test Market Open Capture - Simulate Tokyo Opening

This script simulates a market open event to test the capture system.
It mimics what the scheduler does when a market transitions to OPEN.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from GlobalMarkets.models import Market
from FutureTrading.views.MarketOpenCapture import capture_market_open
from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot


def simulate_tokyo_open():
    """Simulate Tokyo market opening"""
    
    print("=" * 80)
    print("SIMULATING TOKYO MARKET OPEN")
    print("=" * 80)
    print("This will use LIVE RTD quotes from Redis (same data as the futures cards).")
    print("Captured data will appear in the Tokyo (Japan) card via /api/market-opens/latest/.")
    proceed = input("\nProceed to capture live Tokyo data now? (Y/n): ").strip().lower()
    if proceed not in ("", "y", "yes"):  # default yes
        print("\nℹ️  Aborted by user. No changes made.")
        return
    
    # Get Tokyo market
    tokyo = Market.objects.filter(country='Japan').first()
    if not tokyo:
        print("❌ ERROR: Tokyo/Japan market not found in database")
        return
    
    print(f"\n📍 Market: {tokyo.country}")
    print(f"   Timezone: {tokyo.timezone_name}")
    print(f"   Current Status: {tokyo.status}")
    print(f"   Market Hours: {tokyo.market_open_time} - {tokyo.market_close_time}")
    
    # Check for existing sessions today
    from django.utils import timezone
    from datetime import datetime
    
    today = timezone.now().date()
    existing = MarketOpenSession.objects.filter(
        country='Japan',
        captured_at__date=today
    ).order_by('-captured_at')
    
    print(f"\n📊 Existing sessions today: {existing.count()}")
    if existing.exists():
        print("   Recent sessions:")
        for s in existing[:3]:
            print(f"   - Session #{s.session_number}: {s.captured_at.strftime('%H:%M:%S')} - Signal: {s.bhs}")
        
        # Ask to delete existing session
        print("\n⚠️  A session already exists for today!")
        print("   This is due to unique constraint: one session per market per day")
        response = input("\n   Delete existing session and create new one? (y/N): ").strip().lower()
        
        if response == 'y':
            for s in existing:
                # Delete snapshots first
                FutureSnapshot.objects.filter(session=s).delete()
                s.delete()
            print("   ✅ Deleted existing sessions")
        else:
            print("\n   ℹ️  Keeping existing session. Exiting test.")
            return
    
    # Capture the market open
    print("\n" + "=" * 80)
    print("🚀 TRIGGERING CAPTURE...")
    print("=" * 80)
    
    session = capture_market_open(tokyo)
    
    if not session:
        print("\n❌ CAPTURE FAILED - No session returned")
        return
    
    print(f"\n✅ CAPTURE SUCCESSFUL")
    print("=" * 80)
    
    # Display session details
    print(f"\n📋 SESSION DETAILS:")
    print(f"   Session Number: #{session.session_number}")
    print(f"   Country: {session.country}")
    print(f"   Captured At: {session.captured_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Total Signal: {session.bhs}")
    print(f"   FW Weight: {session.fw_weight}")
    print(f"   YM Last: {session.ym_last}")
    
    # Get snapshots
    snapshots = FutureSnapshot.objects.filter(session=session).order_by('symbol')
    
    print(f"\n📊 CAPTURED {snapshots.count()} SNAPSHOTS:")
    print("-" * 80)
    
    # Find TOTAL first
    total_snap = snapshots.filter(symbol='TOTAL').first()
    if total_snap:
        print(f"\n🎯 TOTAL COMPOSITE:")
        print(f"   Signal: {total_snap.signal}")
        print(f"   Weight: {total_snap.weight}")
        print(f"   Weighted Average: {total_snap.weighted_average}")
        print(f"   Sum Weighted: {total_snap.sum_weighted}")
        print(f"   Instrument Count: {total_snap.instrument_count}")
        print(f"   Status: {total_snap.status}")
    
    # Display individual futures
    print(f"\n📈 INDIVIDUAL FUTURES:")
    print("-" * 80)
    
    futures = snapshots.exclude(symbol='TOTAL')
    for snap in futures:
        print(f"\n{snap.symbol}:")
        print(f"   Last: {snap.last_price}")
        print(f"   Change: {snap.change} ({snap.change_percent}%)")
        print(f"   Signal: {snap.signal} (Weight: {snap.weight})")
        print(f"   Bid: {snap.bid} x {snap.bid_size}  |  Ask: {snap.ask} x {snap.ask_size}")
        print(f"   24h Range: {snap.low_24h} - {snap.high_24h} (Range: {snap.range_diff_24h}, {snap.range_pct_24h}%)")
        print(f"   52w Range: {snap.week_52_low} - {snap.week_52_high}")
        if snap.entry_price:
            print(f"   Entry: {snap.entry_price} | Dynamic High: {snap.high_dynamic} | Dynamic Low: {snap.low_dynamic}")
    
    # Verification summary
    print("\n" + "=" * 80)
    print("🔍 VERIFICATION SUMMARY:")
    print("=" * 80)
    
    issues = []
    
    # Check TOTAL
    if not total_snap:
        issues.append("❌ No TOTAL snapshot found")
    else:
        if not total_snap.signal or total_snap.signal == '':
            issues.append("❌ TOTAL signal is empty")
        if total_snap.weighted_average is None:
            issues.append("❌ TOTAL weighted_average is None")
    
    # Check individual futures
    for snap in futures:
        missing = []
        if not snap.signal or snap.signal == '':
            missing.append("signal")
        if snap.weight is None:
            missing.append("weight")
        if snap.change_percent is None:
            missing.append("change_percent")
        if snap.low_24h is None or snap.high_24h is None:
            missing.append("24h_range")
        if snap.week_52_low is None and snap.week_52_high is None:
            missing.append("52w_range")
        
        if missing:
            issues.append(f"❌ {snap.symbol} missing: {', '.join(missing)}")
    
    if not issues:
        print("\n✅ ALL CHECKS PASSED!")
        print("   - TOTAL composite present with signal and weighted average")
        print("   - All futures have signal, weight, change%, 24h range")
        print("   - 52w ranges populated where available")
    else:
        print("\n⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    try:
        simulate_tokyo_open()
    except Exception as e:
        print(f"\n💥 EXCEPTION OCCURRED:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        print("\n📋 TRACEBACK:")
        traceback.print_exc()
        sys.exit(1)
