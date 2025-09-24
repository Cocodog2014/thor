from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
import json


class TradingData(models.Model):
    """Trading data with hybrid storage: key fields as columns, rest as JSON."""
    
    # Core identification fields
    no_trades = models.IntegerField(db_index=True, help_text="Number of trades")
    dlst = models.CharField(max_length=50, db_index=True, help_text="DLST identifier")
    
    # Date/time fields for efficient querying
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)
    date = models.IntegerField(db_index=True)
    day = models.CharField(max_length=20)
    
    # Core financial data
    open_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, help_text="Opening price")
    close_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, help_text="Closing price")
    volume = models.BigIntegerField(null=True, blank=True, db_index=True, help_text="Trading volume")
    
    # World market summary fields for quick access
    world_net_change = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    world_net_perc_change = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    world_high = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    world_low = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    
    # JSON field for all other data (130+ columns)
    additional_data = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="All other trading indicators and AI data stored as JSON"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-month', '-date']
        indexes = [
            models.Index(fields=['year', 'month', 'date']),
            models.Index(fields=['dlst', 'year', 'month']),
            models.Index(fields=['no_trades']),
            models.Index(fields=['volume']),
        ]
        unique_together = ['no_trades', 'dlst', 'year', 'month', 'date']
    
    def __str__(self):
        return f"Trading#{self.no_trades} {self.dlst} {self.year}-{self.month:02d}-{self.date:02d}"
    
    @property
    def date_display(self):
        """Human readable date display."""
        return f"{self.year}-{self.month:02d}-{self.date:02d}"
    
    def get_indicator(self, indicator_name):
        """Helper to get any indicator from additional_data."""
        return self.additional_data.get(indicator_name)


class ImportJob(models.Model):
    """Tracks a large Excel import job."""
    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='PENDING')  # PENDING, RUNNING, COMPLETED, FAILED
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"ImportJob({self.file_name}) - {self.status}"
