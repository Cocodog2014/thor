from __future__ import annotations
"""Deprecated import path.

The realtime job provider now lives in ThorTrading.studies.realtime_provider.
Keep this module as a compatibility shim so settings and callers importing
ThorTrading.realtime.provider continue to work.
"""

from ThorTrading.studies.realtime_provider import *  # noqa: F403

