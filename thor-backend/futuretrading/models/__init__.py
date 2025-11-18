"""
FutureTrading.models package

Novice-friendly structure:
- rtd.py        → Real-time data models (existing instruments, weights, etc.)
- market_open.py→ Market-open capture models (to be added in Phase 1)

This __init__ re-exports models so imports like
`from FutureTrading.models import TradingInstrument` continue to work.
"""

from .rtd import *  # noqa: F401,F403
# Market open models (CamelCase filename per user's preference)
try:
    from .MarketSession import *  # noqa: F401,F403
except Exception:
    # During initial scaffold there may be no MarketOpen models yet
    pass

# 52-week tracking models
try:
    from .extremes import *  # noqa: F401,F403
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]
