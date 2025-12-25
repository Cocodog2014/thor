from __future__ import annotations
"""Compatibility shim for legacy imports.

The flush logic now lives in ThorTrading.services.intraday.flush. Prefer importing
from that module directly. This shim will be removed once callers migrate.
"""

from ThorTrading.services.intraday.flush import flush_closed_bars  # noqa: F401
