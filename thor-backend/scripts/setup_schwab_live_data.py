#!/usr/bin/env python
"""
Setup SchwabLiveData provider configuration for Futures Trading.
This creates the ConsumerApp, DataFeed, and routing needed for the futures dashboard.

Run: python scripts/setup_schwab_live_data.py
"""

import django
import os
import sys

# Setup Django
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from SchwabLiveData.models import ConsumerApp, DataFeed


def main():
    print("="*70)
    print("SETTING UP SCHWAB LIVE DATA PROVIDER")
    print("="*70)
    
    # 1. Create or get the Excel Live feed
    print("\n[1/2] Creating Data Feed: Excel Live (ThinkOrSwim)")
    excel_feed, created = DataFeed.objects.get_or_create(
        code='excel_live',
        defaults={
            'display_name': 'Excel Live - ThinkOrSwim',
            'description': 'Real-time data from ThinkOrSwim via Excel RTD',
            'connection_type': 'excel_rtd',
            'provider_key': 'excel_live',
            'is_active': True,
        }
    )
    print(f"  {'✓ Created' if created else '→ Using existing'}: {excel_feed.display_name}")
    
    # 2. Create Futures Trading Consumer App
    print("\n[2/2] Creating Consumer App: Futures Trading")
    
    # Create the consumer without letting get_or_create handle the validation
    try:
        consumer = ConsumerApp.objects.get(code='futures_trading')
        # Update existing
        if consumer.primary_feed != excel_feed:
            consumer.primary_feed = excel_feed
            consumer.save()
            print(f"  → Updated existing: {consumer.display_name} now uses {excel_feed.display_name}")
        else:
            print(f"  → Using existing: {consumer.display_name}")
    except ConsumerApp.DoesNotExist:
        # Create new - manually call clean() to populate fields, then save
        consumer = ConsumerApp(
            code='futures_trading',
            is_active=True,
            primary_feed=excel_feed,
        )
        consumer.clean()  # Manually trigger clean to populate display_name and authorized_capabilities
        consumer.save()  # Now save will work
        print(f"  ✓ Created: {consumer.display_name}")
    
    print(f"     Primary Feed: {consumer.primary_feed.display_name if consumer.primary_feed else 'None'}")
    print(f"     Status: {'Active' if consumer.is_active else 'Inactive'}")
    
    # Verify
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    print(f"✓ Data Feeds: {DataFeed.objects.count()}")
    print(f"✓ Consumer Apps: {ConsumerApp.objects.count()}")
    
    print("\n✓ SCHWAB LIVE DATA SETUP COMPLETE!")
    print("\nThe futures dashboard will now:")
    print("  1. Use /api/schwab/quotes/latest as primary endpoint")
    print("  2. Pull data from Excel Live (ThinkOrSwim RTD)")
    print("  3. Route through SchwabLiveData provider abstraction")
    print("\nNext steps:")
    print("  1. Revert the frontend changes (we need to use the SchwabLiveData endpoints)")
    print("  2. Refresh your futures dashboard - the 404 error should be gone!")
    print("="*70)


if __name__ == '__main__':
    main()
