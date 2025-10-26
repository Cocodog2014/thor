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
    
    # YM Price Data at Capture
    ym_open = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ym_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ym_ask = models.DecimalField(max_digits=10, decimal_places=2, help_text="Ask price at capture")
    ym_bid = models.DecimalField(max_digits=10, decimal_places=2, help_text="Bid price at capture")
    ym_last = models.DecimalField(max_digits=10, decimal_places=2, help_text="Last traded price")
    
    # Entry and Target Prices
    ym_entry_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                         help_text="Actual entry (Ask if buying, Bid if selling)")
    ym_high_dynamic = models.DecimalField(max_digits=10, decimal_places=2, 
                                          help_text="Entry + 20 points ($100 profit target)")
    ym_low_dynamic = models.DecimalField(max_digits=10, decimal_places=2, 
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
                             help_text="TOTAL signal")
    weight = models.IntegerField(null=True, blank=True, help_text="TOTAL weight (e.g., -3)")
    sum_weighted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       help_text="Sum weighted (e.g., 13.02)")
    instrument_count = models.IntegerField(null=True, blank=True, default=11,
                                           help_text="Count of instruments (typically 11)")
    status = models.CharField(max_length=20, blank=True, help_text="Status (e.g., LIVE TOTAL)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['session', 'symbol']
        unique_together = ['session', 'symbol']
        verbose_name = 'Future Snapshot'
        verbose_name_plural = 'Future Snapshots'
    
    def __str__(self):
        return f"{self.symbol} - {self.session.country} - {self.session.captured_at.strftime('%Y-%m-%d')}"


__all__ = ['MarketOpenSession', 'FutureSnapshot']
