"""Quick test: Manually trigger heartbeat to test WebSocket broadcast"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
django.setup()

from thor_project.realtime.engine import run_heartbeat, HeartbeatContext
from core.infra.jobs import JobRegistry
from thor_project.realtime.registry import register_jobs
from channels.layers import get_channel_layer
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Build registry
registry = JobRegistry()
register_jobs(registry)

# Get channel layer
channel_layer = get_channel_layer()
logger.info(f"Channel layer: {channel_layer}")

# Create context
ctx = HeartbeatContext(
    logger=logger,
    shared_state={},
    channel_layer=channel_layer
)

# Run heartbeat for 5 seconds (fast tick = 1 second, so 5 ticks)
# Heartbeat broadcasts every 30 ticks, so set tick counter manually
print("Testing heartbeat with WebSocket broadcast...")

# Simulate a few ticks to hit the broadcast threshold
import time

# Patch run_heartbeat to run for limited time
original_sleep = time.sleep
tick_count = [0]

def mock_sleep(duration):
    tick_count[0] += 1
    if tick_count[0] >= 35:  # Run 35 ticks (35 seconds in fast mode)
        raise KeyboardInterrupt("Test timeout")
    original_sleep(0.1)  # Actually sleep 0.1 seconds for speed

time.sleep = mock_sleep

try:
    run_heartbeat(
        registry=registry,
        tick_seconds=1.0,
        ctx=ctx,
        channel_layer=channel_layer,
    )
except KeyboardInterrupt:
    print(f"Test completed after {tick_count[0]} ticks")

print("✅ Heartbeat test finished - check logs for broadcast messages")
