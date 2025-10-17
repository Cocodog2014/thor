#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

# TODO: Update to use LiveData/shared/redis_client.py
# from SchwabLiveData.provider_factory import ProviderConfig, get_market_data_provider

print("⚠️  This script needs updating - old SchwabLiveData.provider_factory no longer exists")
print("Use LiveData/shared/redis_client.py instead")
exit(1)

# Test Excel Live provider directly
print('=== Testing Excel Live Provider ===')

# Create config for Excel Live
config = ProviderConfig()
config.provider = 'excel_live'

try:
    provider = get_market_data_provider(config)
    print(f'Provider: {provider.__class__.__name__}')
    
    # Test provider health
    health = provider.health_check()
    print(f'Health: {health}')
    
    # Get quotes
    quotes = provider.get_latest_quotes(['/YM', '/ES', '/NQ'])
    print(f'Quotes type: {type(quotes)}')
    
    if isinstance(quotes, dict):
        rows = quotes.get('rows', [])
        print(f'Rows in response: {len(rows)}')
        
        if rows:
            print('\n=== Sample Row ===')
            sample = rows[0]
            print(f'Symbol: {sample.get("instrument", {}).get("symbol")}')
            print(f'Price: {sample.get("price")}')
            print(f'Change: {sample.get("change")}')
            print(f'Extended data: {sample.get("extended_data")}')
        else:
            print('No rows returned from provider')
    else:
        print(f'Unexpected response format: {quotes}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()