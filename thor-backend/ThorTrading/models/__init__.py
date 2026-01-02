from __future__ import annotations
"""
ThorTrading.models package

Novice-friendly structure:
- rtd.py        → Real-time data models (existing instruments, weights, etc.)
- market_open.py→ Market-open capture models (to be added in Phase 1)

This __init__ re-exports models so imports like
`from ThorTrading.models import TradingInstrument` continue to work.
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


# Register new models for intraday and 24h session
try:
    from .MarketIntraDay import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .Market24h import *  # noqa: F401,F403
except Exception:
    pass
from .Instrument_Intraday import InstrumentIntraday  # noqa: F401

# Study configuration models (join tables, instrument attachments)
try:
    from .study import *  # noqa: F401,F403
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]

