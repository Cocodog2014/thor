import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'thor_project.settings'
import django
django.setup()
from FutureTrading.models.MarketSession import MarketSession
from django.db.models import Max
from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.market_metrics import MarketCloseMetric, MarketRangeMetric

country = 'USA'
latest = MarketSession.objects.filter(country=country).aggregate(Max('session_number'))['session_number__max']
print('Latest session for', country, latest)
if latest:
    print('Before:')
    for s in MarketSession.objects.filter(country=country, session_number=latest):
        print(f"{s.future:5} close={s.market_close} range={s.market_range}")
    enriched,_ = get_enriched_quotes_with_composite()
    cu = MarketCloseMetric.update_for_country_on_close(country, enriched)
    ru = MarketRangeMetric.update_for_country_on_close(country)
    print('\nApplied CloseMetric rows updated:', cu, 'RangeMetric rows updated:', ru)
    print('After:')
    for s in MarketSession.objects.filter(country=country, session_number=latest):
        print(f"{s.future:5} close={s.market_close} range={s.market_range}")
else:
    print('No sessions found for country')
