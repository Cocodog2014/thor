import logging
from django.core.exceptions import ValidationError
from django.db import models

from .constants import CONTROL_COUNTRY_CHOICES, ALLOWED_CONTROL_COUNTRIES
from GlobalMarkets.services.market_clock import (
    get_market_time,
    is_market_open_now as svc_is_open,
    get_market_status as svc_get_status,
    should_collect_data as svc_should_collect,
)
from GlobalMarkets.services.composite import calculate_global_composite as svc_calculate_composite

logger = logging.getLogger(__name__)


class Market(models.Model):
    """
    Represents stock markets around the world for monitoring while trading US markets
    """
    # Basic market information
    country = models.CharField(max_length=50, choices=CONTROL_COUNTRY_CHOICES)

    # Timezone information
    timezone_name = models.CharField(max_length=50)

    # Trading hours (in local market time)
    market_open_time = models.TimeField()
    market_close_time = models.TimeField()

    # Market status - controls data collection
    status = models.CharField(
        max_length=10,
        choices=[('OPEN', 'Open'), ('CLOSED', 'Closed')],
        default='CLOSED'
    )

    # Control market configuration
    is_control_market = models.BooleanField(default=False)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)

    # Market configuration
    is_active = models.BooleanField(default=True)

    # Additional market info
    currency = models.CharField(max_length=3, blank=True)

    # Futures capture control flags
    enable_futures_capture = models.BooleanField(default=True)
    enable_open_capture = models.BooleanField(default=True)
    enable_close_capture = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country']
        verbose_name = 'Market'
        verbose_name_plural = 'Markets'

    def __str__(self):
        return f"{self.country} ({self.timezone_name})"

    def get_display_name(self):
        display_names = {
            'Japan': 'Tokyo',
            'China': 'Shanghai',
            'India': 'Bombay',
            'Germany': 'Frankfurt',
            'United Kingdom': 'London',
            'Pre_USA': 'Pre_USA',
            'USA': 'USA',
            'Canada': 'Toronto',
            'Mexico': 'Mexican'
        }
        return display_names.get(self.country, self.country)

    def _canonicalize_country(self, raw: str) -> str:
        if raw is None:
            raise ValidationError({"country": "Country is required."})
        value = raw.strip()
        if value not in ALLOWED_CONTROL_COUNTRIES:
            raise ValidationError({
                "country": (
                    f"Unsupported market country '{value}'. Allowed: {sorted(ALLOWED_CONTROL_COUNTRIES)}"
                )
            })
        return value

    def save(self, *args, **kwargs):
        self.country = self._canonicalize_country(self.country)
        return super().save(*args, **kwargs)

    def get_sort_order(self):
        order_map = {
            'Japan': 1,
            'China': 2,
            'India': 3,
            'Germany': 4,
            'United Kingdom': 5,
            'Pre_USA': 6,
            'USA': 7,
            'Canada': 8,
            'Mexico': 9,
        }
        return order_map.get(self.country, 999)

    # Service-backed helpers (keep public API stable)
    def get_current_market_time(self):
        return get_market_time(self)

    def is_market_open_now(self):
        return svc_is_open(self)

    def get_market_status(self):
        return svc_get_status(self)

    def should_collect_data(self):
        return svc_should_collect(self)

    @classmethod
    def calculate_global_composite(cls):
        return svc_calculate_composite(cls)
