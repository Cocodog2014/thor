from __future__ import annotations
from typing import Any, Dict

from ThorTrading.studies.registry import register


class FuturesTotalStudy:
    key = "FUTURES_TOTAL"
    name = "Futures TOTAL Composite"

    def compute(self, *, quotes: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        # We will paste your existing logic here next.
        return {
            "signal": "HOLD",
            "per_symbol": {},
            "total": {},
        }


# Register on import
register(FuturesTotalStudy())
