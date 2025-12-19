from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import time

from GlobalMarkets.models.market import Market


# THE 9 CONTROL MARKETS - Global Market Drivers
# These markets represent 100% of weighted global market influence
EXPECTED_MARKETS = [
    # Asia - 25% weight
    {
        'country': 'Japan', 
        'timezone_name': 'Asia/Tokyo', 
        'market_open_time': time(9, 0), 
        'market_close_time': time(15, 0), 
        'currency': 'JPY', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.25  # Tokyo (Nikkei) - Primary Asian session driver
    },
    
    # China - 10% weight
    {
        'country': 'China', 
        'timezone_name': 'Asia/Shanghai', 
        'market_open_time': time(9, 30), 
        'market_close_time': time(15, 0), 
        'currency': 'CNY', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.10  # Shanghai (SSE) - Mainland sentiment
    },
    
    # India - 5% weight
    {
        'country': 'India', 
        'timezone_name': 'Asia/Kolkata', 
        'market_open_time': time(9, 15), 
        'market_close_time': time(15, 30), 
        'currency': 'INR', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.05  # Bombay (Sensex) - Emerging market proxy
    },
    
    # Europe - 20% weight
    {
        'country': 'Germany', 
        'timezone_name': 'Europe/Berlin', 
        'market_open_time': time(9, 0), 
        'market_close_time': time(17, 30), 
        'currency': 'EUR', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.20  # Frankfurt (DAX) - Core Eurozone
    },
    
    # UK - 5% weight
    {
        'country': 'United Kingdom', 
        'timezone_name': 'Europe/London', 
        'market_open_time': time(8, 0), 
        'market_close_time': time(16, 30), 
        'currency': 'GBP', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.05  # London (FTSE) - Early Europe sentiment
    },
    
    # Pre-USA - 5% weight
    {
        'country': 'Pre_USA', 
        'timezone_name': 'America/New_York', 
        'market_open_time': time(8, 30), 
        'market_close_time': time(9, 30), 
        'currency': 'USD', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.05  # CME Globex Futures - Bridge between sessions
    },
    
    # Americas - 25% weight
    {
        'country': 'USA', 
        'timezone_name': 'America/New_York', 
        'market_open_time': time(9, 30), 
        'market_close_time': time(16, 0), 
        'currency': 'USD', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.25  # New York (S&P/Dow/NASDAQ) - Global leader
    },
    
    # Canada - 3% weight
    {
        'country': 'Canada', 
        'timezone_name': 'America/Toronto', 
        'market_open_time': time(9, 30), 
        'market_close_time': time(16, 0), 
        'currency': 'CAD', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.03  # Toronto (TSX) - Commodity confirmation
    },
    
    # Mexico - 2% weight
    {
        'country': 'Mexico', 
        'timezone_name': 'America/Mexico_City', 
        'market_open_time': time(8, 30), 
        'market_close_time': time(15, 0), 
        'currency': 'MXN', 
        'status': 'OPEN', 
        'is_active': True,
        'is_control_market': True,
        'weight': 0.02  # BMV IPC - Regional follow-through
    },
]


class Command(BaseCommand):
    help = "Seed the 9 global control markets with their weights (100% total influence)"

    def handle(self, *args, **options):
        with transaction.atomic():
            expected_countries = [m['country'] for m in EXPECTED_MARKETS]
            
            # Deactivate any markets not in our control list
            deactivated = Market.objects.exclude(country__in=expected_countries).update(
                is_active=False, 
                is_control_market=False,
                weight=0.00
            )

            created = 0
            updated = 0
            for data in EXPECTED_MARKETS:
                obj, is_created = Market.objects.get_or_create(
                    country=data['country'],
                    defaults=data
                )
                if is_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Created {data['country']} (weight: {data['weight']*100}%)"
                    ))
                else:
                    # Update existing
                    for field, value in data.items():
                        if field != 'country':
                            setattr(obj, field, value)
                    obj.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(
                        f"  ↻ Updated {data['country']} (weight: {data['weight']*100}%)"
                    ))
        
        # Verify total weight = 1.00 (100%)
        total_weight = sum([m['weight'] for m in EXPECTED_MARKETS])
        active_count = Market.objects.filter(is_active=True, is_control_market=True).count()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seed complete!"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Created: {created}, Updated: {updated}, Deactivated: {deactivated}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Active control markets: {active_count}/9"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Total weight: {total_weight*100}%"
        ))
