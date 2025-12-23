"""
ThorTrading.views package

Organized by concern:
- RTD.py                  → Real-time quotes API endpoints
- MarketSession.py        → Market session API endpoints
- MarketOpenCapture.py    → Market open capture logic
- MarketGrader.py         → Market grading logic

This __init__ re-exports primary views so existing imports keep working.
"""

try:
    from .RTD import LatestQuotesView  # noqa: F401
    from .MarketSession import *  # noqa: F401, F403
    from .MarketOpenCapture import capture_market_open  # noqa: F401
    # Grader runs via heartbeat job; legacy thread starter retained for compatibility
    from .MarketGrader import start_grading_service  # noqa: F401
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]

