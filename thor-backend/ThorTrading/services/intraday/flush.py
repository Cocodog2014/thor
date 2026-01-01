"""Backward-compatible shim.

The intraday implementation now lives in `ThorTrading.studies.futures_total.intraday`.
Keep this module for existing imports.
"""

from __future__ import annotations

from ThorTrading.studies.futures_total.intraday.flush import flush_closed_bars

__all__ = ["flush_closed_bars"]
