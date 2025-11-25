"""
Market-Open Capture models

Captures market snapshots at regional opens for futures trading analysis.
Single-table design: one row per future per market open event.
Tracks trades based on TOTAL composite signals and grades outcomes.
"""

from django.db import models
from django.utils import timezone

# Grouping support



class MarketSession(models.Model):
    """
    Captures one future at one market open event.
    Single-table design: 12 rows per market open (one for each future + TOTAL).
    Enables easy filtering by future or market without joins.
    """

    # Identification
    session_number = models.IntegerField(help_text="Trade counter/sequence number")
    capture_group = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Group identifier for all rows captured in the same market-open event"
    )

    # Date/Time Info
    year = models.IntegerField()
    month = models.IntegerField()
    date = models.IntegerField(help_text="Day of month")
    day = models.CharField(max_length=10, help_text="Day of week (Mon, Tue, etc.)")
    captured_at = models.DateTimeField(default=timezone.now, help_text="Exact timestamp of capture")

    # Market Info
    country = models.CharField(max_length=50, help_text="Market region (Japan, China, Europe, USA, etc.)")
    future = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[
            ('TOTAL', 'TOTAL Composite'),
            ('YM', 'Dow Jones (YM)'),
            ('ES', 'S&P 500 (ES)'),
            ('NQ', 'NASDAQ (NQ)'),
            ('RTY', 'Russell 2000 (RTY)'),
            ('CL', 'Crude Oil (CL)'),
            ('SI', 'Silver (SI)'),
            ('HG', 'Copper (HG)'),
            ('GC', 'Gold (GC)'),
            ('VX', 'Volatility (VX)'),
            ('DX', 'Dollar Index (DX)'),
            ('ZB', 'Bonds (ZB)'),
        ],
        help_text="Future symbol for this capture row",
    )
    country_future = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Numeric country future metric kept next to future for ordering",
    )
    weight = models.IntegerField(
        null=True,
        blank=True,
        help_text="Weight value (for TOTAL)",
    )

    # Signal placed immediately after future for desired physical ordering
    bhs = models.CharField(
        max_length=20,
        choices=[
            ('BUY', 'Buy'),
            ('STRONG_BUY', 'Strong Buy'),
            ('SELL', 'Sell'),
            ('STRONG_SELL', 'Strong Sell'),
            ('HOLD', 'Hold'),
        ],
        help_text="Signal from TOTAL or individual future",
    )

    # Optional window/outcome status (lightweight, no grading logic stored elsewhere)
    wndw = models.CharField(
        max_length=20,
        choices=[
            ('WORKED', 'Worked'),
            ("DIDNT_WORK", "Didn't Work"),
            ('NEUTRAL', 'Neutral'),
            ('PENDING', 'Pending'),
        ],
        default='PENDING',
        null=True,
        blank=True,
        help_text="Window/outcome label (Worked / Didn't Work / Neutral / Pending)",
    )

    # Removed outcome/status grading fields; wndw reintroduced as optional label
    country_future_wndw_total = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Country-level total for wndw aggregation",
    )

    # Live Price Data at Market Open (bid/ask should follow wndw for physical ordering requirements)
    bid_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Bid price at capture",
    )
    bid_size = models.IntegerField(null=True, blank=True, help_text="Bid size")
    last_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Last traded price at market open",
    )
    spread = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Bid-Ask spread",
    )
    ask_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Ask price at capture",
    )
    ask_size = models.IntegerField(null=True, blank=True, help_text="Ask size")

    # Entry and targets
    entry_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Actual entry (Ask if buying, Bid if selling)",
    )

    # ▶ Target hit tracking (placed after entry_price for logical grouping)
    TARGET_HIT_CHOICES = [
        ('TARGET', 'Profit Target'),
        ('STOP', 'Stop Loss'),
    ]

    target_hit_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Price at which the first target or stop was hit",
    )
    target_hit_type = models.CharField(
        max_length=10,
        choices=TARGET_HIT_CHOICES,
        null=True,
        blank=True,
        help_text="Which level was hit first: profit TARGET or STOP",
    )

    target_high = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Configurable target above entry (per TargetHighLowConfig)",
    )
    target_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Configurable stop below entry (per TargetHighLowConfig)",
    )
    target_hit_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the first target or stop was hit",
    )

    # Additional market data
    volume = models.BigIntegerField(null=True, blank=True, help_text="Trading volume")
    vwap = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Volume Weighted Average Price",
    )
    market_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market open move (number)",
    )
    market_high_number = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="High move from open (number)",
    )
    market_high_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="High move from open (percent)",
    )
    market_low_number = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Low move from open (number)",
    )
    market_low_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Low move from open (percent)",
    )
    market_close_number = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Close move from open (number)",
    )
    market_close_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Close move from open (percent)",
    )
    market_range_number = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Intraday range (number)",
    )
    market_range_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Intraday range (percent)",
    )
    session_close = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Previous close price",
    )
    session_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Open price",
    )
    open_vs_prev_number = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Open vs Prev (Number)",
    )
    open_vs_prev_percent = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Open vs Prev (%)",
    )
    day_24h_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24 hour low",
    )
    day_24h_high = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24 hour high",
    )
    range_high_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Range (24h High - 24h Low)",
    )
    range_percent = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Range as % of previous close",
    )

    # 52-Week Range Data
    week_52_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week low",
    )
    week_52_high = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week high",
    )
    week_52_range_high_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week range (High - Low)",
    )
    week_52_range_percent = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week range as % of current price",
    )

    # Signal & Composite Data
    # For TOTAL row: weighted_average and composite signal
    # For individual futures: their own signal/HBS
    weighted_average = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="TOTAL weighted average (e.g., -0.109)",
    )
    instrument_count = models.IntegerField(
        null=True,
        blank=True,
        default=11,
        help_text="Count of instruments (for TOTAL)",
    )

    # Signal outcome metrics kept together near instrument_count for consistent export ordering
    strong_buy_worked = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Strong buy signals that worked",
    )
    strong_buy_worked_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong buys that worked",
    )
    strong_buy_didnt_work = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Strong buy signals that did not work",
    )
    strong_buy_didnt_work_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong buys that failed",
    )
    buy_worked = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Buy signals that worked",
    )
    buy_worked_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of buys that worked",
    )
    buy_didnt_work = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Buy signals that did not work",
    )
    buy_didnt_work_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of buys that failed",
    )
    hold = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Hold signals count",
    )
    hold_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of holds",
    )
    strong_sell_worked = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Strong sell signals that worked",
    )
    strong_sell_worked_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong sells that worked",
    )
    strong_sell_didnt_work = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Strong sell signals that failed",
    )
    strong_sell_didnt_work_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong sells that failed",
    )
    sell_worked = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sell signals that worked",
    )
    sell_worked_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of sells that worked",
    )
    sell_didnt_work = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sell signals that failed",
    )
    sell_didnt_work_percentage = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of sells that failed",
    )

    # Removed legacy strong_sell_flag (no longer tracked)

    class Meta:
        ordering = ['-captured_at', 'future']
        unique_together = ['country', 'year', 'month', 'date', 'future']
        verbose_name = 'Market Session'
        verbose_name_plural = 'Market Sessions'

    def __str__(self):
        return f"{self.country} - {self.future} - {self.year}/{self.month}/{self.date} - {self.bhs}"


__all__ = ['MarketSession']
