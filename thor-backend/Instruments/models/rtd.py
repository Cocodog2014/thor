"""Compatibility shim.

RTD models were moved to `ThorTrading.studies.futures_total.models.rtd`.

Keep this module to avoid churn across imports like `from Instruments.models.rtd import ...`.
"""

from ThorTrading.studies.futures_total.models.rtd import (  # noqa: F401
    ContractWeight,
    InstrumentCategory,
    SIGNAL_CHOICES,
    SignalStatValue,
    SignalWeight,
    TradingInstrument,
)

__all__ = [
    "InstrumentCategory",
    "TradingInstrument",
    "SIGNAL_CHOICES",
    "SignalStatValue",
    "SignalWeight",
    "ContractWeight",
]
