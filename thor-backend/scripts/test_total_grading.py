import os
import sys
import django

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from ThorTrading.studies.futures_total.services.sessions.grading import MarketGrader
from ThorTrading.models.MarketSession import MarketSession

grader = MarketGrader()

# Get TOTAL session
total = MarketSession.objects.filter(country='USA', symbol='TOTAL', wndw='PENDING').order_by('-captured_at').first()

if not total:
    print("No pending TOTAL session found")
else:
    print(f"TOTAL Session #{total.session_number}")
    print(f"  Signal: {total.bhs}")
    print(f"  Entry: {total.entry_price}")
    print(f"  Target H: {total.target_high}")
    print(f"  Target L: {total.target_low}")
    print(f"  Status: {total.wndw}")
    
    # Test get_current_price
    print("\nTesting get_current_price('TOTAL', 'BUY'):")
    price = grader.get_current_price('TOTAL', total.bhs)
    print(f"  Result: {price}")
    
    if price:
        print(f"\nEvaluation:")
        if total.bhs in ['BUY', 'STRONG_BUY']:
            print(f"  Long trade - exit at BID")
            if price >= total.target_high:
                print(f"  ✓ {price} >= {total.target_high} → WORKED")
            elif price <= total.target_low:
                print(f"  ✗ {price} <= {total.target_low} → DIDNT_WORK")
            else:
                print(f"  ⏸ {price} between {total.target_low} and {total.target_high} → PENDING")
    
    # Now try grading it
    print("\n" + "="*60)
    print("Attempting to grade TOTAL session...")
    print("="*60)
    result = grader.grade_session(total)
    print(f"Grade result: {result}")
    
    # Refresh from DB
    total.refresh_from_db()
    print(f"TOTAL status after grading: {total.wndw}")
    if total.target_hit_price:
        print(f"Hit price: {total.target_hit_price}")
        print(f"Hit type: {total.target_hit_type}")
        print(f"Hit at: {total.target_hit_at}")

