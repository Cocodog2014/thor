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

from ThorTrading.studies.futures_total.models.market_session import MarketSession

latest_groups = (
    MarketSession.objects
    .values('session_number')
    .order_by('-session_number')
    .distinct()[:5]
)

print("Latest session_number values (top 5):")
for g in latest_groups:
    session_number = g['session_number']
    count = MarketSession.objects.filter(session_number=session_number).count()
    countries = (MarketSession.objects
                 .filter(session_number=session_number)
                 .values_list('country', flat=True)
                 .distinct())
    print(f"  session_number={session_number}: rows={count}, countries={', '.join(countries)}")

# Show sample rows for newest group ordered as in admin
if latest_groups:
    newest = latest_groups[0]['session_number']
    rows = (MarketSession.objects
            .filter(session_number=newest)
            .order_by('future')
            .values('future','country','last_price','bhs')[:15])
    print(f"\nFirst 15 rows in newest session_number {newest} ordered by future:")
    for r in rows:
        print(r)

