#!/usr/bin/env python
"""
OBSOLETE: Old SchwabLiveData setup script.

The old DataFeed/ConsumerApp models no longer exist.
The new LiveData structure uses Redis pub/sub - no database configuration needed.
"""

print("="*70)
print("⚠️  This script is obsolete")
print("="*70)
print("\nThe old SchwabLiveData models (DataFeed, ConsumerApp) no longer exist.")
print("The new LiveData structure uses Redis pub/sub.")
print("\nNo setup needed - just subscribe to Redis channels:")
print("  - live_data:quotes:{symbol}")
print("  - live_data:positions:{account_id}")
print("="*70)
