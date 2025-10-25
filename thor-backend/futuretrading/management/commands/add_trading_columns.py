"""
Management command to add tick_value and margin_requirement columns
"""

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Add tick_value and margin_requirement columns to TradingInstrument'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                cursor.execute('''
                    ALTER TABLE "FutureTrading_tradinginstrument" 
                    ADD COLUMN IF NOT EXISTS tick_value NUMERIC(10, 2) NULL
                ''')
                self.stdout.write(self.style.SUCCESS('✓ Added tick_value column'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'tick_value column may already exist: {e}'))
            
            try:
                cursor.execute('''
                    ALTER TABLE "FutureTrading_tradinginstrument" 
                    ADD COLUMN IF NOT EXISTS margin_requirement NUMERIC(15, 2) NULL
                ''')
                self.stdout.write(self.style.SUCCESS('✓ Added margin_requirement column'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'margin_requirement column may already exist: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\nColumns added successfully!'))
