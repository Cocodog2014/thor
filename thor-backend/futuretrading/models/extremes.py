"""
52-Week High/Low Tracking Model

Tracks rolling 52-week extremes based on incoming LAST prices.
Admin can seed initial values, then system auto-updates on new highs/lows.
"""

from django.db import models
from django.utils import timezone
from django.dispatch import Signal
from decimal import Decimal


week52_extreme_changed = Signal()


class Rolling52WeekStatsManager(models.Manager):
    """Custom manager providing batch update capability.

    update_batch(prices) accepts a mapping of symbol->last_price (Decimal|str|float).
    For each existing record it applies update_from_price; new records are NOT
    created here (seed separately) to keep logic explicit.
    Returns a list of (symbol, extreme_type, old_value, new_value, date) events.
    """

    def update_batch(self, prices: dict):
        if not prices:
            return []
        events = []
        # Normalize prices to Decimal
        normalized = {}
        for sym, val in prices.items():
            try:
                normalized[sym] = Decimal(str(val))
            except Exception:
                continue
        # Fetch only existing symbols to avoid accidental creation
        for stats in self.filter(symbol__in=normalized.keys()):
            stats_events = stats.update_from_price(normalized[stats.symbol], emit_signal=True)
            events.extend(stats_events)
        return events


class Rolling52WeekStats(models.Model):
    """
    Tracks 52-week high/low extremes for each trading instrument.
    
    Workflow:
    1. Admin seeds initial high_52w/low_52w values (one-time setup)
    2. System automatically updates when new LAST price exceeds extremes
    3. Dates track when each extreme was set
    """
    
    symbol = models.CharField(
        max_length=10,
        unique=True,
        help_text="Trading symbol (YM, ES, NQ, etc.)"
    )
    
    # 52-Week High
    high_52w = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Highest price in last 52 weeks"
    )
    high_52w_date = models.DateField(
        help_text="Date when 52w high was set"
    )
    
    # 52-Week Low
    low_52w = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Lowest price in last 52 weeks"
    )
    low_52w_date = models.DateField(
        help_text="Date when 52w low was set"
    )
    
    # Metadata
    last_price_checked = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Most recent LAST price that was checked"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    # Optional: Track all-time extremes too
    all_time_high = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="All-time high (optional)"
    )
    all_time_high_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when all-time high was set"
    )
    all_time_low = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="All-time low (optional)"
    )
    all_time_low_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when all-time low was set"
    )
    
    class Meta:
        verbose_name = "52-Week Stats"
        verbose_name_plural = "52-Week Stats"
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol}: H={self.high_52w} L={self.low_52w}"
    
    objects = Rolling52WeekStatsManager()

    def stale_hours(self) -> float | None:
        """Return number of hours since last extreme update or None if never checked."""
        if not self.last_updated:
            return None
        delta = timezone.now() - self.last_updated
        return round(delta.total_seconds() / 3600.0, 2)

    def update_from_price(self, last_price: Decimal, emit_signal: bool = False) -> bool | list:
        """
        Check if incoming LAST price sets new high/low and update if so.
        
        Args:
            last_price: Current LAST price from market data
            
        Returns:
            bool|list: True if any extreme updated (legacy); or list of events when emit_signal=True.
        """
        updated = False
        events = []
        today = timezone.now().date()
        
        # Check for new high
        if last_price > self.high_52w:
            prev = self.high_52w
            self.high_52w = last_price
            self.high_52w_date = today
            updated = True
            events.append((self.symbol, 'HIGH_52W', prev, last_price, today))

            # Also update all-time high (only after initial seed exists for both extremes)
            if (self.all_time_high is None or last_price > self.all_time_high) and self.low_52w_date and self.high_52w_date:
                prev_at = self.all_time_high
                self.all_time_high = last_price
                self.all_time_high_date = today
                events.append((self.symbol, 'ALL_TIME_HIGH', prev_at, last_price, today))
        
        # Check for new low
        if last_price < self.low_52w:
            prev = self.low_52w
            self.low_52w = last_price
            self.low_52w_date = today
            updated = True
            events.append((self.symbol, 'LOW_52W', prev, last_price, today))

            # Also update all-time low (only after initial seed exists for both extremes)
            if (self.all_time_low is None or last_price < self.all_time_low) and self.low_52w_date and self.high_52w_date:
                prev_at = self.all_time_low
                self.all_time_low = last_price
                self.all_time_low_date = today
                events.append((self.symbol, 'ALL_TIME_LOW', prev_at, last_price, today))
        
        # Always track last checked price
        self.last_price_checked = last_price
        
        if updated:
            self.save()
            if emit_signal and events:
                # fire individual signals for each event
                for (symbol, extreme_type, old_value, new_value, date) in events:
                    week52_extreme_changed.send(
                        sender=Rolling52WeekStats,
                        instance=self,
                        symbol=symbol,
                        extreme_type=extreme_type,
                        old_value=old_value,
                        new_value=new_value,
                        date=date,
                    )

        if emit_signal:
            return events
        return updated
    
    def to_dict(self):
        """Return as dict for Redis/API serialization"""
        return {
            'symbol': self.symbol,
            'high_52w': str(self.high_52w),
            'high_52w_date': self.high_52w_date.isoformat(),
            'low_52w': str(self.low_52w),
            'low_52w_date': self.low_52w_date.isoformat(),
            'all_time_high': str(self.all_time_high) if self.all_time_high else None,
            'all_time_high_date': self.all_time_high_date.isoformat() if self.all_time_high_date else None,
            'all_time_low': str(self.all_time_low) if self.all_time_low else None,
            'all_time_low_date': self.all_time_low_date.isoformat() if self.all_time_low_date else None,
            'last_updated': self.last_updated.isoformat(),
            'stale_hours': self.stale_hours(),
        }
