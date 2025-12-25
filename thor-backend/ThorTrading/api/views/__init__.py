from __future__ import annotations
"""API views mapped into the ThorTrading.api namespace."""

from .market_close import MarketCloseCaptureView
from .market_grader import (
    MarketGrader,
    grade_pending_once,
    grader,
    start_grading_service,
    stop_grading_service,
)
from .market_open import MarketOpenCaptureView
from .market_sessions import (
    LatestPerMarketOpensView,
    LatestPerMarketSessionsView,
    MarketOpenSessionDetailView,
    MarketOpenSessionListView,
    MarketOpenStatsView,
    MarketSessionDetailView,
    MarketSessionListView,
    MarketSessionStatsView,
    PendingMarketOpensView,
    PendingMarketSessionsView,
    TodayMarketOpensView,
    TodayMarketSessionsView,
)
from .quotes import LatestQuotesView, RibbonQuotesView

__all__ = [
    # Market capture endpoints
    "MarketOpenCaptureView",
    "MarketCloseCaptureView",
    # Market grading
    "MarketGrader",
    "grade_pending_once",
    "grader",
    "start_grading_service",
    "stop_grading_service",
    # Market session views
    "MarketSessionListView",
    "MarketSessionDetailView",
    "TodayMarketSessionsView",
    "PendingMarketSessionsView",
    "MarketSessionStatsView",
    "LatestPerMarketSessionsView",
    "MarketOpenSessionListView",
    "MarketOpenSessionDetailView",
    "TodayMarketOpensView",
    "PendingMarketOpensView",
    "MarketOpenStatsView",
    "LatestPerMarketOpensView",
    # Quote views
    "LatestQuotesView",
    "RibbonQuotesView",
]
