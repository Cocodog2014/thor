"""
Management command to run the Market Open Grading service.

Usage:
    python manage.py grade_market_opens

This will start a background loop that checks pending trades every 0.5 seconds.
"""

from django.core.management.base import BaseCommand
from FutureTrading.views.MarketGrader import start_grading_service


class Command(BaseCommand):
    help = 'Run the Market Open Grading service (checks every 0.5 seconds)'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Market Open Grader...'))
        self.stdout.write('Press Ctrl+C to stop')
        
        try:
            start_grading_service()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nGrading service stopped'))
