# ThorTrading/models/Instrument_Intraday.py
from __future__ import annotations

from django.db import models


class InstrumentIntraday(models.Model):
    """
    Instrument intraday 1-minute OHLCV bars (global scope).

    Truth table for intraday:
      - One row per (symbol, timestamp_minute)
      - timestamp_minute should be the minute bucket in UTC

    Everything else (market session, 24h, 52w) is derived by filtering/aggregating
    this table by time windows and lookbacks.
    """

    # Minute bucket (store UTC)
    timestamp_minute = models.DateTimeField(
        db_index=True,
        help_text="Minute bucket (UTC). Example: 2025-12-26 17:51:00+00:00",
    )

    # Instrument identity
    symbol = models.CharField(max_length=32, db_index=True)

    # 1-minute OHLCV
    open_1m = models.DecimalField(max_digits=18, decimal_places=4)
    high_1m = models.DecimalField(max_digits=18, decimal_places=4)
    low_1m = models.DecimalField(max_digits=18, decimal_places=4)
    close_1m = models.DecimalField(max_digits=18, decimal_places=4)
    volume_1m = models.BigIntegerField(default=0)

    # Optional quote context (last seen bid/ask/spread near the minute close)
    bid_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ask_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    spread_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "Instruments_instrumentintraday"
        verbose_name = "Instrument Intraday Bar"
        verbose_name_plural = "Instrument Intraday Bars"

        constraints = [
            models.UniqueConstraint(
                fields=["timestamp_minute", "symbol"],
                name="uniq_intraday_symbol_minute",
            )
        ]

        indexes = [
            # The workhorse index for virtually all queries (charts, 24h, sessions, 52w)
            models.Index(fields=["symbol", "timestamp_minute"], name="idx_intraday_instr_sym_ts"),

            # Useful for housekeeping / debugging / partitions later
            models.Index(fields=["timestamp_minute"], name="idx_intraday_instr_ts"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.symbol} {self.timestamp_minute:%Y-%m-%d %H:%M} "
            f"O={self.open_1m} H={self.high_1m} L={self.low_1m} C={self.close_1m}"
        )