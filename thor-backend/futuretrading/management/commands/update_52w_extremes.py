"""
Management command to update 52-week extremes from incoming LAST prices.

Run this periodically (every 5 minutes during market hours, or once per day after close).
Reads latest quotes from Redis and updates extremes if new highs/lows detected.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.models.extremes import Rolling52WeekStats
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update 52-week high/low extremes from latest market prices'
    
    # All futures we're tracking (normalized names)
    SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
    
    # Map normalized symbol names to Redis keys (handle Excel RTD naming)
    SYMBOL_MAP = {
        'RTY': 'RT',           # Russell 2000 comes in as RT
        'ZB': '30YRBOND',      # 30-Year Bond comes in as 30YRBOND
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to update (default: all 11 futures)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each symbol',
        )
    
    def handle(self, *args, **options):
        symbols = options.get('symbols') or self.SYMBOLS
        verbose = options.get('verbose', False)
        
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Checking {len(symbols)} symbols for 52w extreme updates...\n'))
        
        for symbol in symbols:
            try:
                # Map symbol to Redis key (handle Excel RTD naming differences)
                redis_symbol = self.SYMBOL_MAP.get(symbol, symbol)
                
                # Get latest quote from Redis
                quote = live_data_redis.get_latest_quote(redis_symbol)
                
                if not quote or not quote.get('last'):
                    if verbose:
                        self.stdout.write(self.style.WARNING(f'  {symbol}: No data in Redis'))
                    skipped_count += 1
                    continue
                
                last_price = Decimal(str(quote['last']))
                
                # Get or create stats record
                stats, created = Rolling52WeekStats.objects.get_or_create(
                    symbol=symbol,
                    defaults={
                        'high_52w': last_price,
                        'high_52w_date': timezone.now().date(),
                        'low_52w': last_price,
                        'low_52w_date': timezone.now().date(),
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✨ {symbol}: Created new record (H={last_price}, L={last_price})')
                    )
                    updated_count += 1
                    continue
                
                # Check if price updates extremes
                was_updated = stats.update_from_price(last_price)
                
                if was_updated:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  🎯 {symbol}: NEW EXTREME! H={stats.high_52w} ({stats.high_52w_date}), '
                            f'L={stats.low_52w} ({stats.low_52w_date})'
                        )
                    )
                    updated_count += 1
                elif verbose:
                    self.stdout.write(
                        f'  ✓ {symbol}: No change (Last={last_price}, H={stats.high_52w}, L={stats.low_52w})'
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {symbol}: Error - {str(e)}')
                )
                logger.error(f'Error updating 52w stats for {symbol}: {e}', exc_info=True)
                skipped_count += 1
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Complete: {updated_count} updated, {skipped_count} skipped\n'
            )
        )
