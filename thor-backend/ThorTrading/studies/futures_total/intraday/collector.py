from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .flush import flush_closed_bars
from .redis_gateway import get_active_sessions

logger = logging.getLogger(__name__)


def collect_once(*, include_equities: bool = True, include_futures: bool = True) -> Dict[str, Any]:
    """Drain Redis closed-bar queues for the active sessions and persist OHLCV into DB."""

    sessions = get_active_sessions()

    result: Dict[str, Any] = {
        "futures_session": sessions.futures,
        "equities_session": sessions.equities,
        "flushed": [],
        "skipped": [],
    }

    def _flush(kind: str, session_key: Optional[str]) -> None:
        if not session_key:
            result["skipped"].append({"asset": kind, "reason": "no_active_session"})
            return
        flush_closed_bars(session_key)
        result["flushed"].append({"asset": kind, "session_key": session_key})

    if include_futures:
        _flush("futures", sessions.futures)

    if include_equities:
        _flush("equities", sessions.equities)

    return result
