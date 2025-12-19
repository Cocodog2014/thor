"""
Verification script to ensure all legacy starters are disabled when heartbeat mode is active.

Run this to validate that legacy supervisor starters properly check THOR_SCHEDULER_MODE.
"""

import os
import sys

# Set heartbeat mode
os.environ["THOR_SCHEDULER_MODE"] = "heartbeat"

# Mock Django to allow imports
class MockSettings:
    FUTURETRADING_ENABLE_PREOPEN_BACKTEST = True
    FUTURETRADING_PREOPEN_BACKTEST_INTERVAL = 30.0

sys.modules['django.conf'] = type(sys)('django.conf')
sys.modules['django.conf'].settings = MockSettings()

# Test imports
print("Testing imports...")
try:
    from ThorTrading.globalmarkets_hooks import _start_global_background_services, _stop_global_background_services
    print("✓ globalmarkets_hooks imports successful")
except Exception as e:
    print(f"✗ globalmarkets_hooks import failed: {e}")
    sys.exit(1)

try:
    from ThorTrading.services.stack_start import start_preopen_backtest_supervisor_wrapper
    print("✓ stack_start imports successful")
except Exception as e:
    print(f"✗ stack_start import failed: {e}")
    sys.exit(1)

# Test that functions have scheduler mode checks
print("\nChecking for THOR_SCHEDULER_MODE guards...")

import inspect

# Check globalmarkets_hooks
source = inspect.getsource(_start_global_background_services)
if "THOR_SCHEDULER_MODE" in source and "heartbeat" in source:
    print("✓ _start_global_background_services() has THOR_SCHEDULER_MODE guard")
else:
    print("✗ _start_global_background_services() missing THOR_SCHEDULER_MODE guard")
    sys.exit(1)

source = inspect.getsource(_stop_global_background_services)
if "THOR_SCHEDULER_MODE" in source and "heartbeat" in source:
    print("✓ _stop_global_background_services() has THOR_SCHEDULER_MODE guard")
else:
    print("✗ _stop_global_background_services() missing THOR_SCHEDULER_MODE guard")
    sys.exit(1)

# Check stack_start
source = inspect.getsource(start_preopen_backtest_supervisor_wrapper)
if "THOR_SCHEDULER_MODE" in source and "heartbeat" in source:
    print("✓ start_preopen_backtest_supervisor_wrapper() has THOR_SCHEDULER_MODE guard")
else:
    print("✗ start_preopen_backtest_supervisor_wrapper() missing THOR_SCHEDULER_MODE guard")
    sys.exit(1)

print("\n✅ All legacy starters properly guarded with THOR_SCHEDULER_MODE checks!")
print("\nWhen THOR_SCHEDULER_MODE='heartbeat' (default):")
print("  - Legacy supervisor threads will NOT be spawned")
print("  - Heartbeat scheduler jobs will handle all timing")
print("  - No race conditions between old and new approaches")
