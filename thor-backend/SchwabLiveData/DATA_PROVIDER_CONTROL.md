# SchwabLiveData Provider Control Guide

## Overview
The SchwabLiveData provider now requires **explicit configuration** - no automatic fallbacks to Excel Live or any other provider. You have full control over which data sources are active.

## How to Control Data Flow

### Option 1: Django Admin Interface (Easiest)

#### To Enable/Disable Data for Futures Trading:

1. **Go to Django Admin**: http://127.0.0.1:8000/admin/
2. **Navigate to**: SchwabLiveData → Consumer Apps
3. **Find**: "Futures Trading App"
4. **Quick Toggle**: Check or uncheck the "Is active" checkbox in the list view, then click "Save"

OR

5. **Batch Actions**: Select one or more consumers, then choose:
   - ✅ "Enable selected consumers" to turn data ON
   - ❌ "Disable selected consumers" to turn data OFF

#### To Enable/Disable Specific Data Feeds:

1. **Navigate to**: SchwabLiveData → Data Feeds
2. **Find**: "Excel Live - ThinkOrSwim"
3. **Toggle**: Check/uncheck "Is active"
4. **Or use batch actions** to enable/disable multiple feeds at once

### Option 2: Python Shell

```python
python manage.py shell

# Disable futures data
from SchwabLiveData.models import ConsumerApp
consumer = ConsumerApp.objects.get(code='futures_trading')
consumer.is_active = False
consumer.save()
print("✅ Futures data flow DISABLED")

# Enable futures data
consumer.is_active = True
consumer.save()
print("✅ Futures data flow ENABLED")

# Disable the Excel Live feed entirely
from SchwabLiveData.models import DataFeed
feed = DataFeed.objects.get(code='excel_live')
feed.is_active = False
feed.save()
print("✅ Excel Live feed DISABLED")
```

### Option 3: Remove Primary Feed (Nuclear Option)

```python
python manage.py shell

from SchwabLiveData.models import ConsumerApp
consumer = ConsumerApp.objects.get(code='futures_trading')
consumer.primary_feed = None
consumer.save()
print("✅ No data source configured for Futures Trading")
```

## What Happens When Data is Disabled?

When you disable a consumer or feed, the futures dashboard will:
- Show: "No data provider configured"
- Display: Empty rows `[]`
- Show: Zeroed composite total
- Return: HTTP 200 (not an error - just no data)

## Current Configuration

Run this to check current status:

```bash
python manage.py shell -c "
from SchwabLiveData.models import ConsumerApp, DataFeed
print('=== CURRENT CONFIGURATION ===')
print()
for consumer in ConsumerApp.objects.all():
    status = '✅ ACTIVE' if consumer.is_active else '❌ DISABLED'
    feed = consumer.primary_feed.display_name if consumer.primary_feed else 'None'
    feed_active = '✅' if consumer.primary_feed and consumer.primary_feed.is_active else '❌'
    print(f'{status} | {consumer.display_name}')
    print(f'   Feed: {feed_active} {feed}')
    print()
"
```

## Adding Future Data Sources (Schwab API, etc.)

When you want to add the Schwab API or other providers:

1. **Create the Feed**:
   - Go to: SchwabLiveData → Data Feeds → Add
   - Code: `schwab_api`
   - Display Name: `Schwab API`
   - Connection Type: `SCHWAB_API`
   - Provider Key: `schwab`
   - Is Active: ✅

2. **Assign to Consumer**:
   - Go to: SchwabLiveData → Consumer Apps
   - Edit: "Futures Trading App"
   - Primary Feed: Select "Schwab API"
   - Save

3. **Switch Between Providers Anytime** - Just change the Primary Feed dropdown!

## Benefits of This Design

✅ **Explicit Control** - Nothing runs unless you turn it on
✅ **No Hidden Fallbacks** - You know exactly which data source is active
✅ **Easy Switching** - Change providers with a dropdown selection
✅ **Multi-Provider Ready** - Add Schwab API, Polygon, etc. without code changes
✅ **Per-App Configuration** - Different apps can use different providers

## Quick Reference

| Action | Method | Result |
|--------|--------|--------|
| Stop all futures data | Disable "Futures Trading App" consumer | No data flows to dashboard |
| Temporarily pause Excel Live | Disable "Excel Live" feed | All apps using it get no data |
| Switch to Schwab API | Change Primary Feed in consumer | Instant switchover |
| Remove data source | Set Primary Feed to "None" | Explicit "not configured" state |

---

**Last Updated**: After removing automatic excel_live fallback
**Files Modified**: 
- `SchwabLiveData/provider_factory.py` - Removed automatic fallback
- `SchwabLiveData/views.py` - Added check for no provider
- `SchwabLiveData/services/feed_routing.py` - Respect consumer.is_active
- `SchwabLiveData/admin.py` - Added quick toggle actions
