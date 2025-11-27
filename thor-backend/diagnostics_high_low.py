import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'thor_project.settings'
import django
django.setup()

from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.market_metrics import MarketHighMetric, MarketLowMetric
from FutureTrading.models.MarketSession import MarketSession
from django.db.models import Max

country = 'United Kingdom'
rows, _ = get_enriched_quotes_with_composite()
print('Fetched quotes count:', len(rows))
upd_h = MarketHighMetric.update_from_quotes(country, rows)
upd_l = MarketLowMetric.update_from_quotes(country, rows)
latest = MarketSession.objects.filter(country=country).aggregate(Max('session_number'))['session_number__max']
print('Updates High:', upd_h, 'Low:', upd_l, 'Session:', latest)
if latest:
    s = MarketSession.objects.filter(country=country, session_number=latest, future='YM').first()
    if s:
        print('YM post-update: high_num', s.market_high_open, 'high_pct', s.market_high_drawdown_pct, 'low_num', s.market_low_open, 'low_pct', s.market_low_pct_open)
    else:
        print('No YM session row found.')
