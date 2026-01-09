"""URL routes for the GlobalMarkets HTTP API.

This module exists as a stable include target for `GlobalMarkets.urls`.
"""

from django.urls import path

from . import api


app_name = "global_markets"


urlpatterns = [
    # Convenience: allow both `/api/global-markets/` and `/api/global-markets/markets/`.
    path("", api.markets, name="markets_root"),
    path("markets/", api.markets, name="markets"),
]
