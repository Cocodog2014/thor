"""
Management command to monitor global markets and trigger captures at market open.

Run this as a background process during trading hours:
    python manage.py monitor_markets --interval 60

Or as a one-time check:
    python manage.py monitor_markets --once
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from GlobalMarkets.models import Market, USMarketStatus
from FutureTrading.views.MarketOpenCapture import capture_market_open
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor global markets and trigger data capture when markets open'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit (no continuous monitoring)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(self.style.SUCCESS('🌍 Global Markets Monitor Started'))
        self.stdout.write(f'Check interval: {interval} seconds')
        self.stdout.write(f'Mode: {"One-time check" if run_once else "Continuous monitoring"}')
        self.stdout.write('-' * 60)
        
        try:
            while True:
                self.check_markets()
                
                if run_once:
                    self.stdout.write(self.style.SUCCESS('\n✅ One-time check complete'))
                    break
                    
                # Wait for next check
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\n⏹️  Monitor stopped by user'))

    def check_markets(self):
        """Check all markets and update their status based on trading hours"""
        
        # First check if US markets are open today
        us_open = USMarketStatus.is_us_market_open_today()
        
        if not us_open:
            self.stdout.write(
                self.style.WARNING(
                    f'[{timezone.now().strftime("%H:%M:%S")}] '
                    f'US markets closed - skipping all monitoring'
                )
            )
            return
        
        self.stdout.write(f'\n[{timezone.now().strftime("%H:%M:%S")}] Checking markets...')
        
        # Get all active control markets
        markets = Market.objects.filter(is_active=True, is_control_market=True)
        
        for market in markets:
            self.check_single_market(market)

    def check_single_market(self, market):
        """Check a single market and update its status"""
        
        # Get current market status
        is_open_now = market.is_market_open_now()
        current_status = market.status
        
        # Determine what the status SHOULD be
        target_status = 'OPEN' if is_open_now else 'CLOSED'
        
        # Check if status needs to change
        if current_status != target_status:
            self.stdout.write(
                self.style.WARNING(
                    f'  🔄 {market.country:15} | '
                    f'{current_status} → {target_status}'
                )
            )
            
            # Update the status (this will trigger the signal)
            market.status = target_status
            market.save()
            
            # If market just opened, trigger capture explicitly
            if target_status == 'OPEN':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'     └─ 📸 Capturing market open data...'
                    )
                )
                
                try:
                    session = capture_market_open(market)
                    if session:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'        ✅ Session #{session.session_number} created '
                                f'with {session.futures.count()} futures'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'        ❌ Capture failed (no session created)'
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'        ❌ Error: {str(e)}'
                        )
                    )
        else:
            # Status is correct, just log
            status_icon = '🟢' if target_status == 'OPEN' else '🔴'
            
            # Get time to next event
            market_status = market.get_market_status()
            if market_status:
                next_event = market_status.get('next_event', 'unknown')
                seconds = market_status.get('seconds_to_next_event', 0)
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                
                time_str = f'{hours}h {minutes}m' if hours > 0 else f'{minutes}m'
                
                self.stdout.write(
                    f'  {status_icon} {market.country:15} | '
                    f'{target_status:6} | '
                    f'Next {next_event} in {time_str}'
                )
