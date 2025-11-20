"""
Market-Open Capture models

Captures market snapshots at regional opens for futures trading analysis.
Single-table design: one row per future per market open event.
Tracks trades based on TOTAL composite signals and grades outcomes.
"""

from django.db import models
from django.utils import timezone


class MarketSession(models.Model):
    """
    Captures one future at one market open event.
    Single-table design: 12 rows per market open (one for each future + TOTAL).
    Enables easy filtering by future or market without joins.
    """
    
    # Identification
    session_number = models.IntegerField(help_text="Trade counter/sequence number")
    
    # Date/Time Info
    year = models.IntegerField()
    month = models.IntegerField()
    date = models.IntegerField(help_text="Day of month")
    day = models.CharField(max_length=10, help_text="Day of week (Mon, Tue, etc.)")
    captured_at = models.DateTimeField(default=timezone.now, help_text="Exact timestamp of capture")
    
    # Market Info
    country = models.CharField(max_length=50, help_text="Market region (Japan, China, Europe, USA, etc.)")
    future = models.CharField(max_length=10, null=True, blank=True,
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
                                       help_text="Future symbol for this capture row")
    country_future = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Numeric country future metric kept next to future for ordering"
    )
    weight = models.IntegerField(
        null=True,
        blank=True,
        help_text="Weight value (for TOTAL)"
    )
    
    # Signal placed immediately after future for desired physical ordering
    bhs = models.CharField(max_length=20,
                           choices=[
                               ('BUY', 'Buy'),
                               ('STRONG_BUY', 'Strong Buy'),
                               ('SELL', 'Sell'),
                               ('STRONG_SELL', 'Strong Sell'),
                               ('HOLD', 'Hold'),
                           ],
                           help_text="Signal from TOTAL or individual future")
    wndw = models.CharField(
        max_length=20,
        choices=[
            ('WORKED', 'Worked'),
            ('DIDNT_WORK', "Didn't Work"),
            ('NEUTRAL', 'Neutral'),
            ('PENDING', 'Pending'),
        ],
        default='PENDING',
        help_text="Window result (mirrors fw_nwdw)"
    )
    country_future_wndw_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Country-level total for wndw aggregation"
    )
    strong_buy_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Strong buy signals that worked"
    )
    strong_buy_worked_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong buys that worked"
    )
    strong_buy_didnt_work = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Strong buy signals that did not work"
    )
    strong_buy_didnt_work_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong buys that failed"
    )
    buy_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Buy signals that worked"
    )
    buy_worked_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of buys that worked"
    )
    buy_didnt_work = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Buy signals that did not work"
    )
    buy_didnt_work_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of buys that failed"
    )
    hold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hold signals count"
    )
    hold_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of holds"
    )
    strong_sell_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Strong sell signals that worked"
    )
    strong_sell_worked_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong sells that worked"
    )
    strong_sell_didnt_work = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Strong sell signals that failed"
    )
    strong_sell_didnt_work_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of strong sells that failed"
    )
    sell_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sell signals that worked"
    )
    sell_worked_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of sells that worked"
    )
    sell_didnt_work = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sell signals that failed"
    )
    sell_didnt_work_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent of sells that failed"
    )

    # Live Price Data at Market Open (bid/ask should follow wndw for physical ordering requirements)
    session_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Bid price at capture (renamed from reference_bid)")
    bid_size = models.IntegerField(null=True, blank=True, help_text="Bid size")
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Last traded price at market open")
    session_ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Ask price at capture")
    ask_size = models.IntegerField(null=True, blank=True, help_text="Ask size")
    # Keep volume adjacent to ask_size so the physical column layout stays intuitive
    volume = models.BigIntegerField(null=True, blank=True, help_text="Trading volume")
    change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                 help_text="Price change from previous close")
    change_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                         help_text="Percentage change")
    
    # Market Data at Open
    vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                               help_text="Volume Weighted Average Price")
    spread = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text="Bid-Ask spread")
    
    # Session Price Data
    session_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Previous close price (renamed from reference_close)")
    session_open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Open price (renamed from reference_open)")
    open_vs_prev_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              help_text="Open vs Prev (Number)")
    open_vs_prev_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                               help_text="Open vs Prev (%)")
    
    # 24-Hour Range Data
    day_24h_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="24 hour low")
    day_24h_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="24 hour high")
    range_high_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Range (24h High - 24h Low)")
    range_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                        help_text="Range as % of previous close")
    
    # 52-Week Range Data
    week_52_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="52-week low")
    week_52_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="52-week high")
    week_52_range_high_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                                  help_text="52-week range (High - Low)")
    week_52_range_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                                help_text="52-week range as % of current price")
    
    # Entry and Target Prices (auto-calculated on save, based on signal)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Actual entry (Ask if buying, Bid if selling)")
    target_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Entry + 20 points ($100 profit target)")
    target_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    help_text="Entry - 20 points ($100 stop loss)")
    
    # Signal & Composite Data
    # For TOTAL row: weighted_average and composite signal
    # For individual futures: their own signal/HBS
    weighted_average = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                           help_text="TOTAL weighted average (e.g., -0.109)")
    instrument_count = models.IntegerField(null=True, blank=True, default=11,
                                           help_text="Count of instruments (for TOTAL)")
    
    strong_sell_flag = models.BooleanField(default=False, help_text="Flag for strong sell signal")
    study_fw = models.CharField(max_length=50, blank=True, help_text="Study/Framework identifier")
    fw_weight = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                    help_text="Weighted average for composite calculation")
    
    # Outcome Tracking at Market Close (filled during grading)
    outcome = models.CharField(max_length=20, 
                              choices=[
                                  ('WORKED', 'Worked'),
                                  ('DIDNT_WORK', "Didn't Work"),
                                  ('NEUTRAL', 'Neutral'),
                                  ('PENDING', 'Pending'),
                              ],
                              default='PENDING',
                              help_text="Trade outcome for this future")
    didnt_work = models.BooleanField(default=False, help_text="Trade outcome flag (legacy)")
    fw_nwdw = models.CharField(max_length=20, 
                               choices=[
                                   ('WORKED', 'Worked'),
                                   ('DIDNT_WORK', "Didn't Work"),
                                   ('NEUTRAL', 'Neutral'),
                                   ('PENDING', 'Pending'),
                               ],
                               default='PENDING',
                               help_text="Framework status")
    
    # Exit Values at Close
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Price when target or stop was hit")
    exit_time = models.DateTimeField(null=True, blank=True,
                                     help_text="Timestamp when outcome was determined")
    fw_exit_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Exit price value")
    fw_exit_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                          help_text="Exit percentage")
    
    # Stopped Out Data
    fw_stopped_out_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                               help_text="Stopped out price value")
    fw_stopped_out_nwdw = models.CharField(max_length=20, blank=True,
                                           help_text="Stopped out status")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-captured_at', 'future']
        unique_together = ['country', 'year', 'month', 'date', 'future']
        verbose_name = 'Market Session'
        verbose_name_plural = 'Market Sessions'
    
    def __str__(self):
        return f"{self.country} - {self.future} - {self.year}/{self.month}/{self.date} - {self.bhs}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate entry and target prices based on signal"""
        # Only calculate if we have the required data and haven't set entry price manually
        if self.session_bid and self.session_ask and self.bhs and not self.entry_price:
            # Determine entry price based on signal
            if self.bhs in ['BUY', 'STRONG_BUY']:
                self.entry_price = self.session_ask  # Buy at ask
            elif self.bhs in ['SELL', 'STRONG_SELL']:
                self.entry_price = self.session_bid  # Sell at bid
            # HOLD doesn't get an entry price
            
            # Calculate high and low targets if we have an entry price
            if self.entry_price:
                self.target_high = self.entry_price + 20  # +20 points for $100 profit
                self.target_low = self.entry_price - 20   # -20 points for $100 stop
        
        super().save(*args, **kwargs)


__all__ = ['MarketSession']
