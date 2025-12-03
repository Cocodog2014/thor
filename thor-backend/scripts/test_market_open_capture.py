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
from ThorTrading.views.MarketOpenCapture import capture_market_open
from ThorTrading.models.MarketSession import MarketSession


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
    
    # Check for existing sessions today (single-table MarketSession rows)
    from django.utils import timezone
    
    today = timezone.now().date()
    session_numbers = list(
        MarketSession.objects
        .filter(country='Japan', captured_at__date=today)
        .values_list('session_number', flat=True)
        .distinct()
        .order_by('-session_number')
    )

    print(f"\n📊 Existing sessions today: {len(session_numbers)}")
    if session_numbers:
        print("   Recent sessions:")
        for num in session_numbers[:3]:
            latest_row = (
                MarketSession.objects
                .filter(country='Japan', session_number=num)
                .order_by('-captured_at')
                .first()
            )
            captured = latest_row.captured_at.strftime('%H:%M:%S') if latest_row else '—'
            signal = latest_row.bhs if latest_row else '—'
            print(f"   - Session #{num}: {captured} - Signal: {signal}")

        print("\n⚠️  A session already exists for today!")
        response = input("\n   Delete existing session(s) and create new one? (y/N): ").strip().lower()

        if response == 'y':
            MarketSession.objects.filter(
                country='Japan',
                session_number__in=session_numbers
            ).delete()
            print("   ✅ Deleted existing MarketSession rows for today")
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
    
    # Fetch all MarketSession rows for this session number
    capture_rows = MarketSession.objects.filter(
        country=session.country,
        session_number=session.session_number
    )

    print(f"\n📊 CAPTURED {capture_rows.count()} ROWS:")
    print("-" * 80)
    
    total_row = capture_rows.filter(future='TOTAL').first()
    if total_row:
        print(f"\n🎯 TOTAL COMPOSITE:")
        print(f"   Signal: {total_row.bhs}")
        print(f"   Weight: {total_row.weight}")
        print(f"   Weighted Average: {total_row.weighted_average}")
        print(f"   Instrument Count: {total_row.instrument_count}")
    
    print(f"\n📈 INDIVIDUAL FUTURES:")
    print("-" * 80)
    
    futures = capture_rows.exclude(future='TOTAL').order_by('future')
    for snap in futures:
        print(f"\n{snap.future}:")
        print(f"   Last: {snap.last_price}")
        print(f"   Signal: {snap.bhs} (Weight: {snap.weight})")
        print(f"   Bid: {snap.bid_price} x {snap.bid_size}  |  Ask: {snap.ask_price} x {snap.ask_size}")
        print(f"   24h Range: {snap.low_24h} - {snap.high_24h} (Range: {snap.range_diff_24h}, {snap.range_pct_24h}%)")
        print(f"   52w Range: {snap.low_52w} - {snap.high_52w}")
        if snap.entry_price:
            print(f"   Entry: {snap.entry_price} | Target High: {snap.target_high} | Target Low: {snap.target_low}")
    
    # Verification summary
    print("\n" + "=" * 80)
    print("🔍 VERIFICATION SUMMARY:")
    print("=" * 80)
    
    issues = []
    
    # Check TOTAL
    if not total_row:
        issues.append("❌ No TOTAL snapshot found")
    else:
        if not total_row.bhs:
            issues.append("❌ TOTAL signal is empty")
        if total_row.weighted_average is None:
            issues.append("❌ TOTAL weighted_average is None")
    
    # Check individual futures
    for snap in futures:
        missing = []
        if not snap.bhs:
            missing.append("signal")
        if snap.weight is None:
            missing.append("weight")
        if snap.low_24h is None or snap.high_24h is None:
            missing.append("24h_range")
        if snap.low_52w is None and snap.high_52w is None:
            missing.append("52w_range")
        
        if missing:
            issues.append(f"❌ {snap.future} missing: {', '.join(missing)}")
    
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

