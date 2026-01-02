from __future__ import annotations

from django.urls import path

from Instruments.views import UserWatchlistView

urlpatterns = [
    path("watchlist/", UserWatchlistView.as_view(), name="instrument-watchlist"),
]
