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
    country_future_wndw_total = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Historical total count for this country/future window",
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
    # Denormalized 24h close (copied from FutureTrading_24hour.close_24h at US close)
    close_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Global 24h close for this session (set at US close)",
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
    market_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market open move (number)",
    )
    market_high_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="High move from open (number)",
    )
    market_high_pct_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="High move from open (percent)",
    )
    market_low_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Low move from open (number)",
    )
    market_low_pct_open = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Low move from open (percent)",
    )
    market_close = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Close move from open (number)",
    )
    market_high_pct_close = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent distance from intraday high",
    )
    market_low_pct_close = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent distance above intraday low",
    )
    market_close_vs_open_pct = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Close vs open change (percent)",
    )
    market_range = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Intraday range (number)",
    )
    market_range_pct = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Intraday range (percent)",
    )
    # Renamed from session_close -> prev_close_24h
    prev_close_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Previous 24h close price",
    )
    # Renamed from session_open -> open_price_24h
    open_price_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current 24h open price",
    )
    # Renamed from open_vs_prev_number -> open_prev_diff_24h
    open_prev_diff_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24h Open − Prev 24h Close (number)",
    )
    # Renamed from open_vs_prev_percent -> open_prev_pct_24h
    open_prev_pct_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24h Open − Prev 24h Close (%)",
    )
    low_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24 hour low",
    )
    high_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24 hour high",
    )
    range_diff_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24h range difference (High - Low)",
    )
    range_pct_24h = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="24h range as % of previous close",
    )

    # 52-Week Range Data
    low_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week low",
    )
    low_pct_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent above 52-week low relative to current price",
    )
    high_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week high",
    )
    high_pct_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent below 52-week high relative to current price",
    )
    range_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="52-week range (High - Low)",
    )
    range_pct_52w = models.DecimalField(
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

    # Legacy attribute names removed (use new 24h field names directly)


__all__ = ['MarketSession']
