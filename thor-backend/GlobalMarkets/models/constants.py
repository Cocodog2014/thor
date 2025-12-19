import pytz
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

CONTROL_COUNTRY_CHOICES = [(c, c) for c in sorted(ALLOWED_CONTROL_COUNTRIES)]

_TIMEZONE_ALIASES = {
    "Tokyo": "Asia/Tokyo",
    "Japan": "Asia/Tokyo",
    "Shanghai": "Asia/Shanghai",
    "China": "Asia/Shanghai",
    "Bombay": "Asia/Kolkata",
    "India": "Asia/Kolkata",
    "Frankfurt": "Europe/Berlin",
    "Germany": "Europe/Berlin",
    "London": "Europe/London",
    "United Kingdom": "Europe/London",
    "Pre-USA": "America/New_York",
    "Pre_USA": "America/New_York",
    "USA": "America/New_York",
    "Toronto": "America/Toronto",
    "Canada": "America/Toronto",
    "Mexican": "America/Mexico_City",
    "Mexico": "America/Mexico_City",
}

try:
    _DEFAULT_MARKET_TZ = pytz.timezone(getattr(settings, "TIME_ZONE", "UTC"))
except Exception:
    _DEFAULT_MARKET_TZ = pytz.UTC
