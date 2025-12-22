import logging
from django.core.exceptions import ValidationError
from django.db import models

from .constants import CONTROL_COUNTRY_CHOICES, ALLOWED_CONTROL_COUNTRIES, TIMEZONE_CHOICES
from GlobalMarkets.services.market_clock import (
    get_market_time,
    is_market_open_now as svc_is_open,
    get_market_status as svc_get_status,
    should_collect_data as svc_should_collect,
)

logger = logging.getLogger(__name__)


class Market(models.Model):
    """
    Represents stock markets around the world for monitoring while trading US markets
    """
    # Basic market information
    country = models.CharField(max_length=50, choices=CONTROL_COUNTRY_CHOICES)

    # Timezone information
    timezone_name = models.CharField(max_length=50, choices=TIMEZONE_CHOICES)

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
            'Mexico': 'Mexican',
            'Futures': 'CME Futures (GLOBEX)',
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
            'Futures': 10,
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
        from datetime import datetime
        import pytz

        composite_score = 0.0
        active_count = 0
        contributions = {}

        control_markets = list(cls.objects.filter(is_control_market=True, is_active=True))
        total_control_markets = len(control_markets)

        for market in control_markets:
            weight = float(market.weight)
            market_name = market.get_display_name()

            status = None
            try:
                status = market.get_market_status()
            except Exception:
                status = None

            current_state = status.get('current_state') if isinstance(status, dict) else None
            is_active_state = current_state in {'OPEN', 'PRECLOSE'}

            if status is None:
                is_active_state = market.is_market_open_now()

            if is_active_state:
                contribution = weight * 100
                composite_score += contribution
                active_count += 1
                contributions[market_name] = {
                    'weight': weight * 100,
                    'active': True,
                    'contribution': contribution,
                    'state': current_state,
                }
            else:
                contributions[market_name] = {
                    'weight': weight * 100,
                    'active': False,
                    'contribution': 0,
                    'state': current_state,
                }

        return {
            'composite_score': round(composite_score, 2),
            'active_markets': active_count,
            'total_control_markets': total_control_markets,
            'max_possible': 100.0,
            'session_phase': cls._determine_session_phase(),
            'contributions': contributions,
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }

    @classmethod
    def _determine_session_phase(cls):
        from datetime import datetime
        import pytz

        now_utc = datetime.now(pytz.UTC)
        hour = now_utc.hour
        if 0 <= hour < 8:
            return 'ASIAN'
        elif 8 <= hour < 14:
            return 'EUROPEAN'
        elif 14 <= hour < 21:
            return 'AMERICAN'
        else:
            return 'OVERLAP'
