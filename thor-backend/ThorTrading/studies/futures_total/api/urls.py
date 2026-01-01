from __future__ import annotations
"""Futures Total API URL patterns."""

from django.urls import path

from ThorTrading.studies.futures_total.api.views.market_close import MarketCloseCaptureView
from ThorTrading.studies.futures_total.api.views.market_open import MarketOpenCaptureView
from ThorTrading.studies.futures_total.api.views.market_sessions import (
	LatestPerMarketOpensView,
	MarketOpenSessionDetailView,
	MarketOpenSessionListView,
	MarketOpenStatsView,
	PendingMarketOpensView,
	TodayMarketOpensView,
)
from ThorTrading.studies.futures_total.api.views.quotes import LatestQuotesView, RibbonQuotesView

app_name = "ThorTrading"

urlpatterns = [
	path("quotes/latest", LatestQuotesView.as_view(), name="quotes-latest"),
	path("quotes/ribbon", RibbonQuotesView.as_view(), name="quotes-ribbon"),
	path("market-opens/", MarketOpenSessionListView.as_view(), name="market-opens-list"),
	path("market-opens/<int:pk>/", MarketOpenSessionDetailView.as_view(), name="market-opens-detail"),
	path("market-opens/today/", TodayMarketOpensView.as_view(), name="market-opens-today"),
	path("market-opens/latest/", LatestPerMarketOpensView.as_view(), name="market-opens-latest"),
	path("market-opens/pending/", PendingMarketOpensView.as_view(), name="market-opens-pending"),
	path("market-opens/stats/", MarketOpenStatsView.as_view(), name="market-opens-stats"),
	path("market-open/capture", MarketOpenCaptureView.as_view(), name="market-open-capture"),
	path("market-close/capture", MarketCloseCaptureView.as_view(), name="market-close-capture"),
]

__all__ = ["app_name", "urlpatterns"]
