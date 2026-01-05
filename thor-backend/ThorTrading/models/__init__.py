from __future__ import annotations
"""
ThorTrading.models package

Novice-friendly structure:
- rtd.py        → Real-time data models (existing instruments, weights, etc.)
- market_open.py→ Market-open capture models (to be added in Phase 1)

This __init__ re-exports models so imports like
`from ThorTrading.models import TradingInstrument` continue to work.
"""

try:
    from Instruments.models.rtd import (  # noqa: F401
        ContractWeight,
        InstrumentCategory,
        SignalStatValue,
        SignalWeight,
        TradingInstrument,
    )
except Exception:
    # In early migrations / partial installs, Instruments may not be ready.
    pass
# Market open models (CamelCase filename per user's preference)
try:
    from ThorTrading.studies.futures_total.models.market_session import MarketSession  # noqa: F401
except Exception:
    # During initial scaffold there may be no MarketOpen models yet
    pass

# Study configuration models (join tables, instrument attachments)
try:
    from ThorTrading.studies.models.study import *  # noqa: F401,F403
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith('_')]

