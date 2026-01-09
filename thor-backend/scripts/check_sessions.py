"""Check MarketSession data in database"""
import os
import sys
import django

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
django.setup()

from ThorTrading.studies.futures_total.models.market_session import MarketSession
from django.db.models import Count

print("=" * 60)
print("MARKET SESSION DATA CHECK")
print("=" * 60)
print(f"\nTotal sessions: {MarketSession.objects.count()}")

print("\nBy country:")
for c in MarketSession.objects.values('country').annotate(count=Count('id')).order_by('-count'):
    print(f"  {c['country']}: {c['count']}")

print("\nLatest 3 sessions:")
for s in MarketSession.objects.order_by('-captured_at')[:3]:
    print(f"  {s.country} - {s.future} - {s.year}/{s.month}/{s.date} - {s.bhs}")

print("\nLatest per country (for API /latest/):")
from GlobalMarkets.services import get_control_countries

for country in get_control_countries(require_session_capture=True):
    latest = MarketSession.objects.filter(country=country).order_by('-captured_at').first()
    if latest:
        print(f"  {country}: {latest.year}-{latest.month:02d}-{latest.date:02d} @ {latest.captured_at.strftime('%H:%M:%S')}")
    else:
        print(f"  {country}: NO DATA")

