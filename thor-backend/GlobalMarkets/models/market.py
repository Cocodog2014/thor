import logging
from django.db import models

from .constants import TIMEZONE_CHOICES
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
    country = models.CharField(max_length=50)

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
        return self.country

    def get_sort_order(self):
        return self.country.lower()

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

        markets = list(cls.objects.filter(is_active=True))
        total_control_markets = len(markets)

        # Equal-weight placeholder since weights are removed
        weight_each = 1.0 / total_control_markets if total_control_markets else 0.0

        for market in markets:
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
                contribution = weight_each * 100
                composite_score += contribution
                active_count += 1
                contributions[market_name] = {
                    'weight': weight_each * 100,
                    'active': True,
                    'contribution': contribution,
                    'state': current_state,
                }
            else:
                contributions[market_name] = {
                    'weight': weight_each * 100,
                    'active': False,
                    'contribution': 0,
                    'state': current_state,
                }

        return {
            'composite_score': round(composite_score, 2),
            'active_markets': active_count,
            'total_control_markets': total_control_markets,
            'max_possible': 100.0,
            'approx_region_phase_utc': cls._approx_region_phase_utc(),
            'contributions': contributions,
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }

    @classmethod
    def _approx_region_phase_utc(cls):
        from datetime import datetime
        import pytz

        # Heuristic label based only on UTC hour; not authoritative trading logic.
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
