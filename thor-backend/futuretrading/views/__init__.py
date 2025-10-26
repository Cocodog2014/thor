"""
FutureTrading.views package

Organized by concern:
- RTD.py                  → Real-time quotes API endpoints
- MarketOpen.py           → Market open sessions API endpoints
- MarketOpenCapture.py    → Market open capture logic
- MarketOpenGrader.py     → Market open grading logic

This __init__ re-exports primary views so existing imports keep working.
"""

try:
    from .RTD import LatestQuotesView  # noqa: F401
    from .MarketOpen import *  # noqa: F401, F403
    from .MarketOpenCapture import capture_market_open  # noqa: F401
    from .MarketOpenGrader import start_grading_service  # noqa: F401
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]
