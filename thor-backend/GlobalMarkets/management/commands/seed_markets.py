from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import time

from GlobalMarkets.models import Market


EXPECTED_MARKETS = [
    {'country': 'Japan', 'timezone_name': 'Asia/Tokyo', 'market_open_time': time(9, 0), 'market_close_time': time(15, 0), 'currency': 'JPY', 'status': 'OPEN', 'is_active': True},
    {'country': 'Shenzhen', 'timezone_name': 'Asia/Shanghai', 'market_open_time': time(9, 30), 'market_close_time': time(15, 0), 'currency': 'CNY', 'status': 'OPEN', 'is_active': True},
    {'country': 'Hong Kong', 'timezone_name': 'Asia/Hong_Kong', 'market_open_time': time(9, 30), 'market_close_time': time(16, 0), 'currency': 'HKD', 'status': 'OPEN', 'is_active': True},
    {'country': 'China', 'timezone_name': 'Asia/Shanghai', 'market_open_time': time(9, 30), 'market_close_time': time(15, 0), 'currency': 'CNY', 'status': 'OPEN', 'is_active': True},
    {'country': 'India', 'timezone_name': 'Asia/Kolkata', 'market_open_time': time(9, 15), 'market_close_time': time(15, 30), 'currency': 'INR', 'status': 'OPEN', 'is_active': True},
    {'country': 'Netherlands', 'timezone_name': 'Europe/Amsterdam', 'market_open_time': time(9, 0), 'market_close_time': time(17, 30), 'currency': 'EUR', 'status': 'OPEN', 'is_active': True},
    {'country': 'France', 'timezone_name': 'Europe/Paris', 'market_open_time': time(9, 0), 'market_close_time': time(17, 30), 'currency': 'EUR', 'status': 'OPEN', 'is_active': True},
    {'country': 'Germany', 'timezone_name': 'Europe/Berlin', 'market_open_time': time(9, 0), 'market_close_time': time(17, 30), 'currency': 'EUR', 'status': 'OPEN', 'is_active': True},
    {'country': 'Spain', 'timezone_name': 'Europe/Madrid', 'market_open_time': time(9, 0), 'market_close_time': time(17, 30), 'currency': 'EUR', 'status': 'OPEN', 'is_active': True},
    {'country': 'United Kingdom', 'timezone_name': 'Europe/London', 'market_open_time': time(8, 0), 'market_close_time': time(16, 30), 'currency': 'GBP', 'status': 'OPEN', 'is_active': True},
    {'country': 'Pre_USA', 'timezone_name': 'America/New_York', 'market_open_time': time(8, 30), 'market_close_time': time(17, 0), 'currency': 'USD', 'status': 'OPEN', 'is_active': True},
    {'country': 'USA', 'timezone_name': 'America/New_York', 'market_open_time': time(9, 30), 'market_close_time': time(16, 0), 'currency': 'USD', 'status': 'OPEN', 'is_active': True},
    {'country': 'Canada', 'timezone_name': 'America/Toronto', 'market_open_time': time(9, 30), 'market_close_time': time(16, 0), 'currency': 'CAD', 'status': 'OPEN', 'is_active': True},
    {'country': 'Mexico', 'timezone_name': 'America/Mexico_City', 'market_open_time': time(8, 30), 'market_close_time': time(15, 0), 'currency': 'MXN', 'status': 'OPEN', 'is_active': True},
]


class Command(BaseCommand):
    help = "Seed GlobalMarkets.Market records with the default set of markets in the correct order."

    def handle(self, *args, **options):
        with transaction.atomic():
            expected_countries = [m['country'] for m in EXPECTED_MARKETS]
            # Deactivate any markets not in our list
            Market.objects.exclude(country__in=expected_countries).update(is_active=False)

            created = 0
            updated = 0
            for data in EXPECTED_MARKETS:
                obj, is_created = Market.objects.get_or_create(
                    country=data['country'],
                    defaults=data
                )
                if is_created:
                    created += 1
                else:
                    # Update existing
                    for field, value in data.items():
                        if field != 'country':
                            setattr(obj, field, value)
                    obj.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. Created {created}, updated {updated}, total active: {Market.objects.filter(is_active=True).count()}"
        ))
