"""Backward-compatible shim.

The intraday restructure moved the implementation to `ThorTrading.intraday.flush`.
Keep this module for existing imports.
"""

from __future__ import annotations

from ThorTrading.intraday.flush import flush_closed_bars

__all__ = ["flush_closed_bars"]
