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

from FutureTrading.models.MarketSession import MarketSession

latest_groups = (
    MarketSession.objects
    .values('capture_group')
    .order_by('-capture_group')
    .distinct()[:5]
)

print("Latest capture_group values (top 5):")
for g in latest_groups:
    cg = g['capture_group']
    count = MarketSession.objects.filter(capture_group=cg).count()
    countries = (MarketSession.objects
                 .filter(capture_group=cg)
                 .values_list('country', flat=True)
                 .distinct())
    print(f"  group={cg}: rows={count}, countries={', '.join(countries)}")

# Show sample rows for newest group ordered as in admin
if latest_groups:
    newest = latest_groups[0]['capture_group']
    rows = (MarketSession.objects
            .filter(capture_group=newest)
            .order_by('future')
            .values('future','country','last_price','bhs')[:15])
    print(f"\nFirst 15 rows in newest capture_group {newest} ordered by future:")
    for r in rows:
        print(r)
