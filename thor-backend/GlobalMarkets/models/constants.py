import pytz
from zoneinfo import ZoneInfo
from django.conf import settings

# Control Markets Configuration - The 9 markets that drive global sentiment
CONTROL_MARKET_WEIGHTS = {
    'Japan': 0.25,
    'China': 0.10,
    'India': 0.05,
    'Germany': 0.20,
    'United Kingdom': 0.05,
    'Pre_USA': 0.05,
    'USA': 0.25,
    'Canada': 0.03,
    'Mexico': 0.02,
}

# Canonical control countries (exact strings stored in DB)
ALLOWED_CONTROL_COUNTRIES = {
    "Japan",
    "China",
    "India",
    "Germany",
    "United Kingdom",
    "Pre_USA",
    "USA",
    "Canada",
    "Mexico",
}

# Backward-compatible choices tuple; safe to keep for admin/importers that still reference it.
CONTROL_COUNTRY_CHOICES = [(c, c) for c in sorted(ALLOWED_CONTROL_COUNTRIES)]

# Strict IANA timezone list for admin dropdown (no aliases)
TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.common_timezones]

try:
    _DEFAULT_MARKET_TZ = ZoneInfo(getattr(settings, "TIME_ZONE", "UTC"))
except Exception:
    _DEFAULT_MARKET_TZ = ZoneInfo("UTC")
