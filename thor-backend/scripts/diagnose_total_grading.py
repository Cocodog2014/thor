import os
import sys
import django

# Ensure project root on path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from ThorTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis
from decimal import Decimal

# Get latest USA sessions
latest_usa = MarketSession.objects.filter(country='USA').order_by('-captured_at').first()
if not latest_usa:
    print("No USA sessions found")
    sys.exit(0)

print(f"Latest USA capture: {latest_usa.captured_at}")
print(f"Session number: {latest_usa.session_number}\n")

# Get all futures for this session including TOTAL
sessions = MarketSession.objects.filter(
    country='USA',
    session_number=latest_usa.session_number
).order_by('future')

print(f"{'Future':<10} {'Signal':<12} {'Entry':<10} {'Target H':<10} {'Target L':<10} {'Status':<12} {'Hit Price':<10}")
print("=" * 95)

for s in sessions:
    print(f"{s.future:<10} {s.bhs:<12} {str(s.entry_price or '—'):<10} {str(s.target_high or '—'):<10} {str(s.target_low or '—'):<10} {s.wndw or 'PENDING':<12} {str(s.target_hit_price or '—'):<10}")

# Check if TOTAL has the same targets as YM
ym_session = sessions.filter(future='YM').first()
total_session = sessions.filter(future='TOTAL').first()

if ym_session and total_session:
    print("\n" + "=" * 95)
    print("COMPARISON: YM vs TOTAL")
    print("=" * 95)
    print(f"YM Entry:    {ym_session.entry_price}")
    print(f"TOTAL Entry: {total_session.entry_price}")
    print(f"YM Target H: {ym_session.target_high}")
    print(f"TOTAL Target H: {total_session.target_high}")
    print(f"YM Target L: {ym_session.target_low}")
    print(f"TOTAL Target L: {total_session.target_low}")
    print(f"YM Status:   {ym_session.wndw or 'PENDING'}")
    print(f"TOTAL Status: {total_session.wndw or 'PENDING'}")
    
    # Check current YM price
    try:
        ym_data = live_data_redis.get_latest_quote('/YM')
        if ym_data:
            current_bid = ym_data.get('bid')
            current_ask = ym_data.get('ask')
            print(f"\nCurrent YM Bid: {current_bid}")
            print(f"Current YM Ask: {current_ask}")
            
            if total_session.entry_price and total_session.target_high and total_session.target_low:
                if total_session.bhs in ['BUY', 'STRONG_BUY']:
                    exit_price = Decimal(str(current_bid)) if current_bid else None
                    print(f"\nTOTAL is {total_session.bhs} - exit would be at BID: {exit_price}")
                    if exit_price:
                        if exit_price >= total_session.target_high:
                            print(f"✓ Price {exit_price} >= Target {total_session.target_high} → Should be WORKED")
                        elif exit_price <= total_session.target_low:
                            print(f"✗ Price {exit_price} <= Stop {total_session.target_low} → Should be DIDNT_WORK")
                        else:
                            print(f"⏸ Price {exit_price} between {total_session.target_low} and {total_session.target_high} → Still PENDING")
    except Exception as e:
        print(f"\nError checking YM price: {e}")

