"""
Market-Open Capture models

Captures market snapshots at regional opens for trading analysis.
Single-table design: one row per instrument per market open event.
Tracks trades based on TOTAL composite signals and grades outcomes.
"""

from django.db import models
from django.utils import timezone
from GlobalMarkets.models.constants import CONTROL_COUNTRY_CHOICES
from ThorTrading.services.config.country_codes import normalize_country_code


class MarketSession(models.Model):
    """
    Captures one instrument at one market open event.
    Single-table design: multiple rows per market open (one per instrument + TOTAL).
    Enables easy filtering by instrument or market without joins.
    """

    # Identification
    session_number = models.IntegerField(help_text="Trade counter/sequence number")
    capture_group = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Group identifier for all rows captured in the same market-open event",
    )
    capture_kind = models.CharField(
        max_length=20,
        default="OPEN",
        db_index=True,
        choices=[
            ("OPEN", "Open"),
            ("CLOSE", "Close"),
            ("OTHER", "Other"),
        ],
        help_text="Type of capture event (OPEN, CLOSE, OTHER)",
    )

    # Date / Time
    year = models.IntegerField()
    month = models.IntegerField()
    date = models.IntegerField(help_text="Day of month")
    day = models.CharField(max_length=10, help_text="Day of week (Mon, Tue, etc.)")
    captured_at = models.DateTimeField(
        default=timezone.now,
        help_text="Exact timestamp of capture",
    )

    # Market Info
    country = models.CharField(
        max_length=50,
        choices=CONTROL_COUNTRY_CHOICES,
        help_text="Market region (canonical control market key)",
    )

    symbol = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ("TOTAL", "TOTAL Composite"),
            ("YM", "Dow Jones (YM)"),
            ("ES", "S&P 500 (ES)"),
            ("NQ", "NASDAQ (NQ)"),
            ("RTY", "Russell 2000 (RTY)"),
            ("CL", "Crude Oil (CL)"),
            ("SI", "Silver (SI)"),
            ("HG", "Copper (HG)"),
            ("GC", "Gold (GC)"),
            ("VX", "Volatility (VX)"),
            ("DX", "Dollar Index (DX)"),
            ("ZB", "Bonds (ZB)"),
        ],
        help_text="Instrument symbol for this capture row",
    )

    country_symbol = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Numeric country/instrument metric kept next to symbol for ordering",
    )

    weight = models.IntegerField(
        null=True,
        blank=True,
        help_text="Weight value (for TOTAL)",
    )

    # Signal
    bhs = models.CharField(
        max_length=20,
        choices=[
            ("BUY", "Buy"),
            ("STRONG_BUY", "Strong Buy"),
            ("SELL", "Sell"),
            ("STRONG_SELL", "Strong Sell"),
            ("HOLD", "Hold"),
        ],
        help_text="Signal from TOTAL or individual instrument",
    )

    # Window / outcome label
    wndw = models.CharField(
        max_length=20,
        choices=[
            ("WORKED", "Worked"),
            ("DIDNT_WORK", "Didn't Work"),
            ("NEUTRAL", "Neutral"),
            ("PENDING", "Pending"),
        ],
        default="PENDING",
        null=True,
        blank=True,
        help_text="Window/outcome label",
    )

    country_symbol_wndw_total = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Historical total count for this country/instrument window",
    )

    # Live Price Data at Market Open
    bid_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    bid_size = models.IntegerField(null=True, blank=True)
    last_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    # Denormalized 24h close (copied from MarketTrading24Hour.close_24h at US close)
    close_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    spread = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    ask_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    ask_size = models.IntegerField(null=True, blank=True)

    # Entry and targets
    entry_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    TARGET_HIT_CHOICES = [
        ("TARGET", "Profit Target"),
        ("STOP", "Stop Loss"),
    ]

    target_hit_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    target_hit_type = models.CharField(max_length=10, choices=TARGET_HIT_CHOICES, null=True, blank=True)
    target_high = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    target_low = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    target_hit_at = models.DateTimeField(null=True, blank=True)

    # Market stats (unchanged)
    volume = models.BigIntegerField(null=True, blank=True)
    change = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    change_percent = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    vwap = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_open = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_high_open = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_high_pct_open = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_low_open = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_low_pct_open = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_close = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_high_pct_close = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_low_pct_close = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_close_vs_open_pct = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_range = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    market_range_pct = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    session_volume = models.BigIntegerField(null=True, blank=True)

    # 24h metrics (renamed already)
    prev_close_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_price_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_prev_diff_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_prev_pct_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    low_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    high_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    range_diff_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    range_pct_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    # Composite stats (unchanged)
    weighted_average = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    instrument_count = models.IntegerField(default=11, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.country:
            normalized = normalize_country_code(self.country)
            if normalized:
                self.country = normalized
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-captured_at", "symbol"]
        unique_together = ["capture_group", "symbol"]
        verbose_name = "Market Session"
        verbose_name_plural = "Market Sessions"

    def __str__(self):
        return f"{self.country} - {self.symbol} - {self.year}/{self.month}/{self.date} - {self.bhs}"


__all__ = ["MarketSession"]
