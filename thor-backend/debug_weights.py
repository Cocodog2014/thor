#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.test import RequestFactory
from SchwabLiveData.views import SchwabQuotesView

# Test the API endpoint that frontend calls
rf = RequestFactory()
request = rf.get('/api/schwab/quotes/latest?consumer=futures_trading')

view = SchwabQuotesView()
try:
    response = view.get(request)
    data = response.data
    
    print('=== API Response Analysis ===')
    if 'error' in data:
        print(f'Error: {data["error"]}')
    else:
        rows = data.get('rows', [])
        print(f'Total rows returned: {len(rows)}')
        
        if rows:
            print('\n=== First Row Analysis ===')
            sample = rows[0]
            instrument = sample.get('instrument', {})
            extended = sample.get('extended_data', {})
            
            print(f'Symbol: {instrument.get("symbol")}')
            print(f'Price: {sample.get("price")}')
            print(f'Change: {sample.get("change")}')
            print(f'Extended data keys: {list(extended.keys())}')
            print(f'Contract weight: {extended.get("contract_weight")}')
            print(f'Signal: {extended.get("signal")}')
            print(f'Stat value: {extended.get("stat_value")}')
            print(f'Signal weight: {extended.get("signal_weight")}')
            
        # Check total/composite data
        total = data.get('total', {})
        if total:
            print(f'\n=== Composite Total ===')
            print(f'Sum weighted: {total.get("sum_weighted")}')
            print(f'Average weighted: {total.get("avg_weighted")}')
            print(f'Count: {total.get("count")}')
            print(f'Signal weight sum: {total.get("signal_weight_sum")}')
            print(f'Composite signal: {total.get("composite_signal")}')
        else:
            print('\n=== No Total Data ===')
            
except Exception as e:
    print(f'Error calling API: {e}')
    import traceback
    traceback.print_exc()