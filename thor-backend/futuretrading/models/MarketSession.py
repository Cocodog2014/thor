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

    # Live Price Data at Market Open
    last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Last traded price at market open")
    change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                 help_text="Price change from previous close")
    change_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                         help_text="Percentage change")
    
    # Bid/Ask Data at Market Open
    reference_ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Ask price at capture")
    ask_size = models.IntegerField(null=True, blank=True, help_text="Ask size")
    reference_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Bid price at capture")
    bid_size = models.IntegerField(null=True, blank=True, help_text="Bid size")
    
    # Market Data at Open
    volume = models.BigIntegerField(null=True, blank=True, help_text="Trading volume")
    vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                               help_text="Volume Weighted Average Price")
    spread = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text="Bid-Ask spread")
    
    # Session Price Data
    reference_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Previous close price")
    reference_open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Open price")
    open_vs_prev_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              help_text="Open vs Prev (Number)")
    open_vs_prev_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                               help_text="Open vs Prev (%)")
    reference_last = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Reference last traded price (legacy)")
    
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
    weight = models.IntegerField(null=True, blank=True, help_text="Weight value (for TOTAL)")
    sum_weighted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Sum weighted (e.g., 13.02, for TOTAL)")
    instrument_count = models.IntegerField(null=True, blank=True, default=11,
                                           help_text="Count of instruments (for TOTAL)")
    status = models.CharField(max_length=50, blank=True, help_text="Status (e.g., LIVE TOTAL)")
    
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
    
    # Market Close Data (captured later in the day)
    close_last_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                           help_text="Last price at market close")
    close_change = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Change at close")
    close_change_percent = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                               help_text="Change % at close")
    close_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    help_text="Bid at close")
    close_bid_size = models.IntegerField(null=True, blank=True, help_text="Bid size at close")
    close_ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    help_text="Ask at close")
    close_ask_size = models.IntegerField(null=True, blank=True, help_text="Ask size at close")
    close_volume = models.BigIntegerField(null=True, blank=True, help_text="Volume at close")
    close_vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="VWAP at close")
    close_spread = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Spread at close")
    close_captured_at = models.DateTimeField(null=True, blank=True,
                                             help_text="Timestamp of close capture")
    close_weighted_average = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                                 help_text="TOTAL weighted average at close")
    close_signal = models.CharField(max_length=20, blank=True,
                                    choices=[
                                        ('BUY', 'Buy'),
                                        ('STRONG_BUY', 'Strong Buy'),
                                        ('SELL', 'Sell'),
                                        ('STRONG_SELL', 'Strong Sell'),
                                        ('HOLD', 'Hold'),
                                    ],
                                    help_text="Signal at close")
    close_weight = models.IntegerField(null=True, blank=True, help_text="Weight at close (for TOTAL)")
    close_sum_weighted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                             help_text="Sum weighted at close (for TOTAL)")
    close_instrument_count = models.IntegerField(null=True, blank=True,
                                                 help_text="Instrument count at close (for TOTAL)")
    close_status = models.CharField(max_length=50, blank=True, help_text="Status at close (e.g., CLOSE TOTAL)")
    
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
        if self.reference_bid and self.reference_ask and self.bhs and not self.entry_price:
            # Determine entry price based on signal
            if self.bhs in ['BUY', 'STRONG_BUY']:
                self.entry_price = self.reference_ask  # Buy at ask
            elif self.bhs in ['SELL', 'STRONG_SELL']:
                self.entry_price = self.reference_bid  # Sell at bid
            # HOLD doesn't get an entry price
            
            # Calculate high and low targets if we have an entry price
            if self.entry_price:
                self.target_high = self.entry_price + 20  # +20 points for $100 profit
                self.target_low = self.entry_price - 20   # -20 points for $100 stop
        
        super().save(*args, **kwargs)


__all__ = ['MarketSession']
