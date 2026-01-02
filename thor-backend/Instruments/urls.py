from __future__ import annotations

from django.urls import path

from Instruments.views import InstrumentCatalogView, UserWatchlistView

urlpatterns = [
    path("catalog/", InstrumentCatalogView.as_view(), name="instrument-catalog"),
    path("watchlist/", UserWatchlistView.as_view(), name="instrument-watchlist"),
]
