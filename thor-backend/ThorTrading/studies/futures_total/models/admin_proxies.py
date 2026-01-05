from __future__ import annotations

from ThorTrading.studies.futures_total.models.rtd import SignalStatValue as InstrumentsSignalStatValue
from ThorTrading.studies.futures_total.models.rtd import SignalWeight as InstrumentsSignalWeight


class ThorTradingSignalStatValue(InstrumentsSignalStatValue):
    class Meta:
        proxy = True
        app_label = "ThorTrading"
        verbose_name = "Signal Statistical Value"
        verbose_name_plural = "Signal Statistical Values"


class ThorTradingSignalWeight(InstrumentsSignalWeight):
    class Meta:
        proxy = True
        app_label = "ThorTrading"
        verbose_name = "Signal Weight"
        verbose_name_plural = "Signal Weights"
