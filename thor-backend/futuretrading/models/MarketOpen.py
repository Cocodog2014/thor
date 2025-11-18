"""
Market-Open Capture models

Captures market snapshots at regional opens for futures trading analysis.
Tracks YM trades based on TOTAL composite signals and grades outcomes.
"""

from django.db import models
from django.utils import timezone


class MarketOpenSession(models.Model):
    """
    Main record for each market open capture - one per region per day.
    Stores the composite signal, trade details, and outcome tracking.
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
    future = models.CharField(max_length=10, default='YM', 
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
                                       help_text="Primary future used for reference prices and trading")
    
    # Reference Price Data at Capture (typically from primary index like YM, but stored neutrally)
    # Note: Individual future prices are in FutureSnapshot; these are summary/reference only
    reference_open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Reference open price (e.g., YM open)")
    reference_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Reference close price (e.g., YM previous close)")
    reference_ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Reference ask price at capture")
    reference_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Reference bid price at capture")
    reference_last = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Reference last traded price")
    
    # Entry and Target Prices (auto-calculated on save, based on TOTAL signal)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Actual entry (Ask if buying, Bid if selling)")
    target_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Entry + 20 points ($100 profit target)")
    target_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    help_text="Entry - 20 points ($100 stop loss)")
    
    # Signal & Composite
    total_signal = models.CharField(max_length=20, 
                                    choices=[
                                        ('BUY', 'Buy'),
                                        ('STRONG_BUY', 'Strong Buy'),
                                        ('SELL', 'Sell'),
                                        ('STRONG_SELL', 'Strong Sell'),
                                        ('HOLD', 'Hold'),
                                    ],
                                    help_text="Composite signal from TOTAL weighted average")
    strong_sell_flag = models.BooleanField(default=False, help_text="Flag for strong sell signal")
    study_fw = models.CharField(max_length=50, blank=True, help_text="Study/Framework identifier")
    fw_weight = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                    help_text="Weighted average for composite calculation")
    
    # Outcome Tracking (filled during grading)
    didnt_work = models.BooleanField(default=False, help_text="Trade outcome flag")
    fw_nwdw = models.CharField(max_length=20, 
                               choices=[
                                   ('WORKED', 'Worked'),
                                   ('DIDNT_WORK', "Didn't Work"),
                                   ('NEUTRAL', 'Neutral'),
                                   ('PENDING', 'Pending'),
                               ],
                               default='PENDING',
                               help_text="Framework status")
    
    # Exit Values
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
        ordering = ['-captured_at']
        unique_together = ['country', 'year', 'month', 'date']
        verbose_name = 'Market Open Session'
        verbose_name_plural = 'Market Open Sessions'
    
    def __str__(self):
        return f"{self.country} - {self.year}/{self.month}/{self.date} - {self.total_signal}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate entry and target prices based on TOTAL signal"""
        # Only calculate if we have the required data and haven't set entry price manually
        if self.reference_bid and self.reference_ask and self.total_signal and not self.entry_price:
            # Determine entry price based on signal
            if self.total_signal in ['BUY', 'STRONG_BUY']:
                self.entry_price = self.reference_ask  # Buy at ask
            elif self.total_signal in ['SELL', 'STRONG_SELL']:
                self.entry_price = self.reference_bid  # Sell at bid
            # HOLD doesn't get an entry price
            
            # Calculate high and low targets if we have an entry price
            if self.entry_price:
                self.target_high = self.entry_price + 20  # +20 points for $100 profit
                self.target_low = self.entry_price - 20   # -20 points for $100 stop
        
        super().save(*args, **kwargs)


class FutureSnapshot(models.Model):
    """
    Snapshot of a single future's data at market open.
    One record per future per session (11 futures × sessions).
    """
    
    # Foreign Key to Session
    session = models.ForeignKey(MarketOpenSession, on_delete=models.CASCADE, related_name='futures')
    
    # Symbol Info
    symbol = models.CharField(max_length=10, 
                             choices=[
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
                                 ('TOTAL', 'TOTAL Composite'),
                             ],
                             help_text="Future symbol")
    
    # Live Price Data (not used for TOTAL)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                     help_text="Last traded price")
    change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                 help_text="Price change from previous close")
    change_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                         help_text="Percentage change")
    
    # Bid/Ask Data (not used for TOTAL)
    bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                              help_text="Current bid price")
    bid_size = models.IntegerField(null=True, blank=True, help_text="Bid size")
    ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                              help_text="Current ask price")
    ask_size = models.IntegerField(null=True, blank=True, help_text="Ask size")
    
    # Market Data
    volume = models.BigIntegerField(null=True, blank=True, help_text="Trading volume")
    vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                               help_text="Volume Weighted Average Price")
    spread = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text="Bid-Ask spread")
    
    # Session Data
    close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                               help_text="Previous close price")
    open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                              help_text="Open price")
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
    
    # Entry and Target Prices (for all futures, not just YM)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Ask if buying, Bid if selling")
    high_dynamic = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Entry + 20 points")
    low_dynamic = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Entry - 20 points")
    
    # TOTAL-specific fields (only used when symbol='TOTAL')
    weighted_average = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                           help_text="TOTAL weighted average (e.g., -0.109)")
    signal = models.CharField(max_length=20, blank=True,
                             choices=[
                                 ('BUY', 'Buy'),
                                 ('STRONG_BUY', 'Strong Buy'),
                                 ('SELL', 'Sell'),
                                 ('STRONG_SELL', 'Strong Sell'),
                                 ('HOLD', 'Hold'),
                             ],
                             help_text="TOTAL signal or individual future HBS")
    weight = models.IntegerField(null=True, blank=True, help_text="Weight value")
    sum_weighted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Sum weighted (e.g., 13.02)")
    instrument_count = models.IntegerField(null=True, blank=True, default=11,
                                           help_text="Count of instruments (typically 11)")
    status = models.CharField(max_length=20, blank=True, help_text="Status (e.g., LIVE TOTAL)")
    
    # Grading Outcome (for all futures to track theoretical performance)
    outcome = models.CharField(max_length=20, 
                              choices=[
                                  ('WORKED', 'Worked'),
                                  ('DIDNT_WORK', "Didn't Work"),
                                  ('NEUTRAL', 'Neutral'),
                                  ('PENDING', 'Pending'),
                              ],
                              default='PENDING',
                              help_text="Trade outcome for this future")
    exit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Price when target or stop was hit")
    exit_time = models.DateTimeField(null=True, blank=True,
                                     help_text="Timestamp when outcome was determined")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['session', 'symbol']
        unique_together = ['session', 'symbol']
        verbose_name = 'Future Snapshot'
        verbose_name_plural = 'Future Snapshots'
    
    def __str__(self):
        return f"{self.symbol} - {self.session.country} - {self.session.captured_at.strftime('%Y-%m-%d')}"


class FutureCloseSnapshot(models.Model):
    """
    Snapshot of a single future's data at market close.
    One record per future per session (11 futures × sessions) plus TOTAL.
    Kept separate from open snapshots to avoid schema churn and allow independent timing.
    """

    # Foreign Key to Session (the session created at open for the same country/day)
    session = models.ForeignKey(MarketOpenSession, on_delete=models.CASCADE, related_name='futures_close')

    # Symbol Info
    symbol = models.CharField(max_length=10,
                              choices=[
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
                                  ('TOTAL', 'TOTAL Composite'),
                              ],
                              help_text="Future symbol")

    # Close-time price data (not used for TOTAL except where noted)
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bid_size = models.IntegerField(null=True, blank=True)
    ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ask_size = models.IntegerField(null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)
    vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    spread = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Keep a copy of session ref prices if needed for comparisons
    close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # TOTAL-specific fields when symbol='TOTAL'
    weighted_average = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    signal = models.CharField(max_length=20, blank=True,
                              choices=[
                                  ('BUY', 'Buy'),
                                  ('STRONG_BUY', 'Strong Buy'),
                                  ('SELL', 'Sell'),
                                  ('STRONG_SELL', 'Strong Sell'),
                                  ('HOLD', 'Hold'),
                              ])
    weight = models.IntegerField(null=True, blank=True)
    sum_weighted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    instrument_count = models.IntegerField(null=True, blank=True, default=11)
    status = models.CharField(max_length=20, blank=True, help_text="Status (e.g., CLOSE TOTAL)")

    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['session', 'symbol']
        unique_together = ['session', 'symbol']
        verbose_name = 'Future Close Snapshot'
        verbose_name_plural = 'Future Close Snapshots'

    def __str__(self):
        return f"[CLOSE] {self.symbol} - {self.session.country} - {self.session.captured_at.strftime('%Y-%m-%d')}"


__all__ = ['MarketOpenSession', 'FutureSnapshot', 'FutureCloseSnapshot']
