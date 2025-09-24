"""
Django management command to test the SchwabLiveData provider system.

Usage:
    python manage.py test_provider
    python manage.py test_provider --provider json
    python manage.py test_provider --provider schwab
    python manage.py test_provider --no-simulation
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from SchwabLiveData.provider_factory import get_market_data_provider, get_provider_status, ProviderConfig
import json
import os


class Command(BaseCommand):
    help = 'Test the SchwabLiveData provider system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            choices=['json', 'excel', 'excel_live', 'schwab'],
            help='Override the default provider'
        )
        parser.add_argument(
            '--no-simulation',
            action='store_true',
            help='Disable live price simulation for JSON provider'
        )
        parser.add_argument(
            '--symbols',
            type=str,
            nargs='+',
            default=None,
            help='Specific symbols to test (default: all configured symbols)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing SchwabLiveData Provider System'))
        self.stdout.write('=' * 60)

        # Set environment overrides if provided
        if options['provider']:
            os.environ['DATA_PROVIDER'] = options['provider']
            self.stdout.write(f"Provider override: {options['provider']}")

        if options['no_simulation']:
            os.environ['ENABLE_LIVE_SIMULATION'] = 'false'
            self.stdout.write("Live simulation disabled")

        # Test provider status
        self.stdout.write('\n1. Testing Provider Status:')
        self.stdout.write('-' * 30)
        try:
            status = get_provider_status()
            for key, value in status.items():
                if key == 'health' and isinstance(value, dict):
                    self.stdout.write(f"  {key}:")
                    for subkey, subvalue in value.items():
                        self.stdout.write(f"    {subkey}: {subvalue}")
                else:
                    self.stdout.write(f"  {key}: {value}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error: {e}"))

        # Test provider initialization
        self.stdout.write('\n2. Testing Provider Initialization:')
        self.stdout.write('-' * 35)
        try:
            symbols = options['symbols'] or ProviderConfig.DEFAULT_SYMBOLS
            # Use config-driven provider creation to honor excel/excel_live options
            cfg = ProviderConfig()
            if options['provider']:
                cfg.provider = options['provider']
            provider = get_market_data_provider(cfg)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Provider created: {provider.get_provider_name()}"))
            
            # Test health check
            health = provider.health_check()
            self.stdout.write(f"  Health: {health}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
            return

        # Test quotes fetching
        self.stdout.write('\n3. Testing Quote Fetching:')
        self.stdout.write('-' * 30)
        try:
            # Some providers return dict with 'rows'
            raw = provider.get_latest_quotes(symbols) if hasattr(provider, 'get_latest_quotes') else []
            quotes = raw.get('rows', raw) if isinstance(raw, dict) else raw
            self.stdout.write(self.style.SUCCESS(f"  ✓ Fetched {len(quotes)} quotes"))
            
            if options['format'] == 'json':
                # JSON output
                self.stdout.write('\nQuotes Data (JSON):')
                self.stdout.write(json.dumps(quotes, indent=2))
            else:
                # Table output
                self.stdout.write('\nQuotes Data (Table):')
                self.stdout.write('-' * 80)
                header = f"{'Symbol':<8} {'Last':<10} {'Bid':<10} {'Ask':<10} {'Signal':<12} {'Stat':<8} {'Weight':<8}"
                self.stdout.write(header)
                self.stdout.write('-' * 80)
                
                for quote in quotes:
                    symbol = quote['instrument']['symbol']
                    last = quote['price']
                    bid = quote['bid']
                    ask = quote['ask']
                    signal = quote['extended_data'].get('signal', 'N/A')
                    stat_value = quote['extended_data'].get('stat_value', '0')
                    weight = quote['extended_data'].get('contract_weight', '1')
                    
                    row = f"{symbol:<8} {last:<10} {bid:<10} {ask:<10} {signal:<12} {stat_value:<8} {weight:<8}"
                    self.stdout.write(row)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error fetching quotes: {e}"))
            return

        # Test multiple fetches (if simulation enabled)
        if not options['no_simulation'] and os.getenv('ENABLE_LIVE_SIMULATION', 'true').lower() in ['true', '1']:
            self.stdout.write('\n4. Testing Live Simulation (3 fetches):')
            self.stdout.write('-' * 40)
            
            for i in range(3):
                try:
                    quotes = provider.get_latest_quotes([symbols[0]])  # Just test first symbol
                    quote = quotes[0]
                    price = quote['price']
                    signal = quote['extended_data'].get('signal', 'N/A')
                    self.stdout.write(f"  Fetch {i+1}: {quote['instrument']['symbol']} = {price} ({signal})")
                    
                    # Small delay to show price changes
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Fetch {i+1} failed: {e}"))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Provider test completed!'))
        
        # Show configuration summary
        self.stdout.write('\nConfiguration Summary:')
        self.stdout.write(f"  Provider Type: {os.getenv('DATA_PROVIDER', 'json')}")
        self.stdout.write(f"  Live Simulation: {os.getenv('ENABLE_LIVE_SIMULATION', 'true')}")
        self.stdout.write(f"  JSON File: {ProviderConfig.get_json_file_path()}")
        self.stdout.write(f"  Default Symbols: {len(ProviderConfig.DEFAULT_SYMBOLS)} configured")
        
        # API endpoint info
        self.stdout.write('\nAPI Endpoints:')
        self.stdout.write('  http://127.0.0.1:8000/api/schwab/quotes/latest/')
        self.stdout.write('  http://127.0.0.1:8000/api/schwab/provider/status/')
        self.stdout.write('  http://127.0.0.1:8000/api/schwab/provider/health/')