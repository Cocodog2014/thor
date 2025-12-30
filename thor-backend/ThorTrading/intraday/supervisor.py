# ThorTrading/intraday/supervisor.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

from .collector import collect_once

logger = logging.getLogger(__name__)


@dataclass
class IntradayCollectorSupervisor:
    """
    Step 1: orchestration wrapper only.
    (We will wire this into the realtime provider in Step 2.)
    """

    def tick(self) -> Dict[str, Any]:
        try:
            return collect_once(include_equities=True, include_futures=True)
        except Exception:
            logger.exception("IntradayCollectorSupervisor.tick failed")
            return {"error": "tick_failed"}
