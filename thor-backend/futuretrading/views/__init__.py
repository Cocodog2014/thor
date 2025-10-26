"""
FutureTrading.views package

Novice-friendly split:
- RTD.py         → Real-time quotes endpoints (existing LatestQuotesView)
- MarketOpen.py  → Market-open capture endpoints (to be added in Phase 2)

This __init__ re-exports primary views so existing imports keep working.
"""

try:
    from .RTD import LatestQuotesView  # noqa: F401
except Exception:
    # During refactor the RTD view may still live in views.py; urls will import directly.
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]
