from __future__ import annotations
from django.db import models


class MarketIntraday(models.Model):
    """
    1-minute OHLCV bars for each symbol, every minute.

    Instrument-neutral: works for any instrument identified by (country, symbol).
    Used for charting, ML, and building higher timeframe candles.
    """

    timestamp_minute = models.DateTimeField(
        db_index=True,
        help_text="Minute bucket (UTC)",
    )

    country = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Market region (canonical values only)",
    )

    symbol = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Instrument symbol",
    )

    twentyfour = models.ForeignKey(
        "MarketTrading24Hour",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="intraday_bars",
        help_text="Optional link to the associated 24h market record",
    )

    # 1-minute OHLCV
    open_1m = models.DecimalField(max_digits=18, decimal_places=4)
    high_1m = models.DecimalField(max_digits=18, decimal_places=4)
    low_1m = models.DecimalField(max_digits=18, decimal_places=4)
    close_1m = models.DecimalField(max_digits=18, decimal_places=4)

    volume_1m = models.BigIntegerField()

    # Optional quote context
    bid_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ask_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    spread_last = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        verbose_name = "Market Intraday Bar"
        verbose_name_plural = "Market Intraday Bars"

        constraints = [
            models.UniqueConstraint(
                fields=["timestamp_minute", "symbol", "country"],
                name="uniq_intraday_minute_symbol_country",
            )
        ]

        indexes = [
            models.Index(fields=["symbol", "country", "timestamp_minute"], name="idx_intraday_sym_cty_ts"),
            models.Index(fields=["twentyfour"], name="idx_intraday_twentyfour"),
            models.Index(fields=["timestamp_minute"], name="idx_intraday_ts"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.country} {self.symbol} "
            f"{self.timestamp_minute:%Y-%m-%d %H:%M} "
            f"O={self.open_1m} C={self.close_1m}"
        )

