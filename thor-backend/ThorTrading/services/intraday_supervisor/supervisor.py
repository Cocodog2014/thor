"""Backward-compatible supervisor API (minimal).

This module intentionally does NOT import the legacy intraday supervisor engine.

The production-stable behavior we want right now is:
- the realtime job `intraday_tick` runs the thin collector/flush path
	(`ThorTrading.intraday.supervisor.IntradaySupervisor.tick`).

We keep the historical symbol names here so existing imports continue to work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntradayMarketSupervisor:
	"""Compatibility wrapper.

	Historically this class owned the tick-building engine.
	For now we delegate to the new thin collector supervisor.
	"""

	def step_once(self) -> None:
		from ThorTrading.intraday.supervisor import IntradaySupervisor

		IntradaySupervisor().tick()

	def on_market_open(self, market: Any) -> None:  # pragma: no cover
		return

	def on_market_close(self, market: Any) -> None:  # pragma: no cover
		return


intraday_market_supervisor = IntradayMarketSupervisor()

__all__ = ["IntradayMarketSupervisor", "intraday_market_supervisor"]

