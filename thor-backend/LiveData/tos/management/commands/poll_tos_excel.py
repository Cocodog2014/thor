"""
TOS Excel RTD Poller

Django management command that continuously polls TOS Excel RTD data
and publishes to Redis. Run this in a separate terminal when you want
live data collection.

Usage:
    python manage.py poll_tos_excel
    python manage.py poll_tos_excel --interval 5
    python manage.py poll_tos_excel --file "A:\\Thor\\RTD_TOS.xlsm" --sheet LiveData --range A1:N13
"""

import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from LiveData.tos.excel_reader import get_tos_excel_reader
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Continuously poll TOS Excel RTD data and publish to Redis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=max(1, getattr(settings, 'EXCEL_LIVE_POLL_MS', 200) // 1000) or 1,
            help='Polling interval in seconds (default from settings.EXCEL_LIVE_POLL_MS)'
        )
        parser.add_argument(
            '--file',
            type=str,
            default=getattr(settings, 'EXCEL_DATA_FILE', r'A:\Thor\RTD_TOS.xlsm'),
            help='Path to Excel file'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=getattr(settings, 'EXCEL_SHEET_NAME', 'LiveData'),
            help='Sheet name'
        )
        parser.add_argument(
            '--range',
            type=str,
            default=getattr(settings, 'EXCEL_LIVE_RANGE', 'A1:N13'),
            help='Data range (default from settings)'
        )

    def handle(self, *args, **options):
        interval = max(1, options['interval'])
        file_path = options['file']
        sheet_name = options['sheet']
        data_range = options['range']

        self.stdout.write(self.style.SUCCESS(f'Starting TOS Excel poller...'))
        self.stdout.write(f'  File: {file_path}')
        self.stdout.write(f'  Sheet: {sheet_name}')
        self.stdout.write(f'  Range: {data_range}')
        self.stdout.write(f'  Interval: {interval}s')
        self.stdout.write(self.style.WARNING('Press Ctrl+C to stop'))
        self.stdout.write('')

        poll_count = 0
        error_count = 0

        try:
            while True:
                poll_count += 1
                
                # Try to acquire lock (non-blocking)
                if not live_data_redis.acquire_excel_lock(timeout=10):
                    self.stdout.write(self.style.WARNING(
                        f'[{poll_count}] Excel read in progress by another process, skipping...'
                    ))
                    time.sleep(interval)
                    continue

                try:
                    # Get Excel reader
                    reader = get_tos_excel_reader(file_path, sheet_name, data_range)
                    
                    if not reader:
                        self.stdout.write(self.style.ERROR(
                            f'[{poll_count}] Failed to create Excel reader'
                        ))
                        error_count += 1
                        time.sleep(interval)
                        continue

                    try:
                        # Read data from Excel
                        quotes = reader.read_data(include_headers=True)

                        # Publish each quote to Redis
                        for q in quotes:
                            symbol = q.get('symbol')
                            if not symbol:
                                continue
                            live_data_redis.publish_raw_quote(symbol, q)

                        self.stdout.write(self.style.SUCCESS(
                            f'[{poll_count}] Published {len(quotes)} quotes to Redis '
                            f'(errors: {error_count})'
                        ))

                    finally:
                        # Always disconnect from Excel
                        reader.disconnect()

                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(
                        f'[{poll_count}] Error reading Excel: {e}'
                    ))
                    logger.exception("Excel read error")

                finally:
                    # Always release lock
                    live_data_redis.release_excel_lock()

                # Sleep before next poll
                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'Stopped after {poll_count} polls ({error_count} errors)'
            ))
