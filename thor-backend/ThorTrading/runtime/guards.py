from __future__ import annotations
"""Runtime guard helpers to prevent legacy schedulers from running."""
import os


def assert_heartbeat_mode():
    """Raise if the legacy scheduler mode is enabled.

    Keeps legacy thread-based starters from being reactivated in environments
    where the heartbeat scheduler should be the only driver.
    """
    mode = os.environ.get("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if mode != "heartbeat":
        raise RuntimeError("Legacy scheduler mode not allowed in this environment")


__all__ = ["assert_heartbeat_mode"]
