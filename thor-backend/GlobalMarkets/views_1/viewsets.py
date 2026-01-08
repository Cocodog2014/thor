from datetime import date, timedelta
import os

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import filters, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
)
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from ..models import Market, USMarketStatus, MarketDataSnapshot, UserMarketWatchlist
from ..serializers import (
    MarketSerializer,
    TradingCalendarSerializer,
    MarketDataSnapshotSerializer,
    UserMarketWatchlistSerializer,
)


# -----------------------------------------------------------------------------
# Helpers (no timers; compute-only)
# -----------------------------------------------------------------------------

def _safe_market_status(m: Market) -> dict | None:
    try:
        st = m.get_market_status()
        return st if isinstance(st, dict) else None
    except Exception:
        return None


def _computed_is_open(st: dict | None) -> bool:
    """
    Truth source for "open": computed state from get_market_status(),
    not DB Market.status.
    """
    if not st:
        return False
    state = st.get("current_state")
    return state in {"OPEN", "PRECLOSE"}


# -----------------------------------------------------------------------------
# ViewSets
# -----------------------------------------------------------------------------

class MarketViewSet(viewsets.ModelViewSet):
    """
    Global Markets API.

    ✅ WS-first architecture compatible:
    - Avoids relying on DB Market.status for "open/active" truth
    - Avoids US gating for global markets
    - Avoids .extra()
    - Keeps ordering stable across all admin-managed markets
    """

    queryset = Market.objects.all()
    serializer_class = MarketSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "is_active", "currency"]
    search_fields = ["country", "timezone_name"]
    ordering_fields = ["sort_order", "country", "market_open_time", "created_at"]
    ordering = ["sort_order", "country"]

    def get_permissions(self):
        """
        Fix security: public can read; only admins can write.
        """
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_queryset(self):
        """
        Default list returns all active markets; use filters to scope further.
        """
        return Market.objects.filter(is_active=True)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny], url_path="overview")
    def markets_overview(self, request):
        """
        Return all active markets (overview).
        """
        qs = Market.objects.filter(is_active=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def active_markets(self, request):
        """
        Return markets that are currently trading based on computed state.
        (Does NOT trust DB Market.status.)
        """
        qs = Market.objects.filter(is_active=True)

        results = []
        for m in qs:
            st = _safe_market_status(m)
            if _computed_is_open(st):
                # Return the normal serializer plus computed state if you want.
                results.append({
                    "id": m.id,
                    "country": m.country,
                    "display_name": m.get_display_name() if hasattr(m, "get_display_name") else m.country,
                    "timezone_name": m.timezone_name,
                    "market_open_time": m.market_open_time.strftime("%H:%M") if m.market_open_time else None,
                    "market_close_time": m.market_close_time.strftime("%H:%M") if m.market_close_time else None,
                    "current_state": st.get("current_state") if st else None,
                })

        return Response({"count": len(results), "results": results})

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def live_status(self, request):
        """
        Real-time status for all active markets.

        IMPORTANT:
        - NO US gating here. Global markets operate even when US is closed.
        - Always uses computed get_market_status().
        """
        qs = Market.objects.filter(is_active=True)

        markets = []
        for m in qs:
            st = _safe_market_status(m)
            if st:
                markets.append(st)

        return Response({
            "total_markets": len(markets),
            "markets": markets,
        })

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def live_status_cached(self, request):
        """
        Redis-first live status payload (WS truth blob).

        Reads:
          - thor:global_markets:status
        Fallback:
          - compute from DB methods if Redis missing
        """
        import json
        import time

        # Try redis first
        try:
            from LiveData.shared.redis_client import live_data_redis  # type: ignore
            raw = live_data_redis.client.get("thor:global_markets:status")
            if raw:
                payload = json.loads(raw)
                return Response({"source": "redis", **payload})
        except Exception:
            pass

        # Fallback compute (kept as safety net)
        markets = self.get_queryset()
        results = []
        for m in markets:
            try:
                st = m.get_market_status()
                if not isinstance(st, dict):
                    st = None
            except Exception:
                st = None

            results.append(
                {
                    "market_id": m.id,
                    "country": m.country,
                    "status": m.status,
                    "market_status": st,
                    "server_time": time.time(),
                }
            )

        return Response({"source": "computed", "timestamp": time.time(), "markets": results})


class TradingCalendarViewSet(viewsets.ModelViewSet):
    """
    Exchange trading calendars (US by default via exchange_code="US").
    """
    queryset = USMarketStatus.objects.all()
    serializer_class = TradingCalendarSerializer
    ordering = ["-date"]

    def get_permissions(self):
        # Public can read; only admins can write.
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return [AllowAny()]
        return [IsAdminUser()]

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def today_status(self, request):
        today = date.today()
        exchange = request.query_params.get("exchange_code", "US")
        is_open = USMarketStatus.is_open_today(exchange)

        try:
            status_obj = USMarketStatus.objects.get(exchange_code=exchange, date=today)
            serializer = self.get_serializer(status_obj)
            return Response({"exchange_code": exchange, "is_open": is_open, "status": serializer.data})
        except USMarketStatus.DoesNotExist:
            return Response({
                "exchange_code": exchange,
                "is_open": is_open,
                "status": {
                    "exchange_code": exchange,
                    "date": today,
                    "is_trading_day": is_open,
                    "holiday_name": "" if is_open else "Weekend",
                    "created_at": None,
                },
            })

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def upcoming_holidays(self, request):
        today = date.today()
        exchange = request.query_params.get("exchange_code", "US")
        upcoming = USMarketStatus.objects.filter(
            exchange_code=exchange,
            date__gte=today,
            is_trading_day=False,
        ).order_by("date")[:10]
        serializer = self.get_serializer(upcoming, many=True)
        return Response({"exchange_code": exchange, "holidays": serializer.data})


class MarketDataSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View market data snapshots (read-only).
    """
    queryset = MarketDataSnapshot.objects.all()
    serializer_class = MarketDataSnapshotSerializer
    permission_classes = [IsAuthenticated]  # tighten security; snapshots are internal
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["market", "market_status", "dst_active"]
    ordering_fields = ["collected_at", "market_time"]
    ordering = ["-collected_at"]

    @action(detail=False, methods=["get"])
    def latest_snapshots(self, request):
        """
        Latest snapshot for each market (correct ordering).
        """
        latest_snapshots = []
        markets = Market.objects.filter(is_active=True)

        for market in markets:
            latest = (
                MarketDataSnapshot.objects
                .filter(market=market)
                .order_by("-collected_at")
                .first()
            )
            if latest:
                latest_snapshots.append(latest)

        serializer = self.get_serializer(latest_snapshots, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def market_history(self, request):
        market_id = request.query_params.get("market_id")
        hours = int(request.query_params.get("hours", 24))

        if not market_id:
            return Response({"error": "market_id parameter required"}, status=400)

        since = timezone.now() - timedelta(hours=hours)

        snapshots = (
            MarketDataSnapshot.objects
            .filter(market_id=market_id, collected_at__gte=since)
            .order_by("-collected_at")
        )
        serializer = self.get_serializer(snapshots, many=True)
        return Response(serializer.data)


class UserMarketWatchlistViewSet(viewsets.ModelViewSet):
    """
    User's market watchlist.
    """
    serializer_class = UserMarketWatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Prevent N+1 when serializer includes nested MarketSerializer
        return (
            UserMarketWatchlist.objects
            .filter(user=self.request.user)
            .select_related("market")
            .order_by("order", "id")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        watchlist_orders = request.data.get("watchlist_orders", [])

        for item_data in watchlist_orders:
            watchlist_id = item_data.get("id")
            new_order = item_data.get("order")
            try:
                watchlist_item = UserMarketWatchlist.objects.get(id=watchlist_id, user=request.user)
                watchlist_item.order = new_order
                watchlist_item.save()
            except UserMarketWatchlist.DoesNotExist:
                continue

        return Response({"status": "success"})


# -----------------------------------------------------------------------------
# Function-based endpoints (dev + stats)
# -----------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def worldclock_stats(request):
    """
    WorldClock application statistics.

    IMPORTANT:
    - "currently_trading" is computed from get_market_status() current_state
      (does NOT trust DB Market.status).
    """
    stats = {
        "us_market_open": USMarketStatus.is_open_today("US"),
        "total_markets": Market.objects.filter(is_active=True).count(),
        "total_snapshots": MarketDataSnapshot.objects.count(),
        "total_users_with_watchlists": UserMarketWatchlist.objects.values("user").distinct().count(),
    }

    last_24h = timezone.now() - timedelta(hours=24)
    stats["recent_snapshots"] = MarketDataSnapshot.objects.filter(collected_at__gte=last_24h).count()

    # Compute currently trading from computed status (all active markets)
    currently_trading = []
    qs = Market.objects.filter(is_active=True)

    for m in qs:
        st = _safe_market_status(m)
        if _computed_is_open(st):
            currently_trading.append(m.country)

    stats["currently_trading"] = currently_trading
    stats["active_markets"] = len(currently_trading)

    return Response(stats)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def api_test_page(request):
    """
    Serve the API test page (admin-only).
    """
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_file_path = os.path.join(current_dir, "api_test.html")

    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HttpResponse(html_content, content_type="text/html")
    except FileNotFoundError:
        return HttpResponse(
            "<h1>Error: api_test.html not found</h1>"
            "<p>Make sure api_test.html is in the project root directory</p>",
            content_type="text/html",
        )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def debug_market_times(request):
    """
    Debug endpoint: current market times + ordering (admin-only).
    """
    all_markets = Market.objects.all()
    active_markets = Market.objects.filter(is_active=True)

    qs = Market.objects.filter(is_active=True).order_by("country")

    debug_info = {
        "total_markets_in_db": all_markets.count(),
        "active_markets_count": active_markets.count(),
        "ordered_markets_count": qs.count(),
        "current_time": timezone.now().isoformat(),
        "all_countries": [m.country for m in all_markets],
        "active_countries": [m.country for m in active_markets],
        "markets": [],
    }

    for market in qs:
        st = _safe_market_status(market) or {}
        current_time_info = st.get("current_time")

        debug_info["markets"].append({
            "position": len(debug_info["markets"]) + 1,
            "country": market.country,
            "display_name": market.get_display_name() if hasattr(market, "get_display_name") else market.country,
            "sort_order": market.get_sort_order() if hasattr(market, "get_sort_order") else None,
            "timezone": market.timezone_name,
            "market_hours": f"{market.market_open_time} - {market.market_close_time}",
            "current_time": current_time_info,
            "is_active": market.is_active,
            "db_status": market.status,  # show DB value for debugging only
            "computed_state": st.get("current_state"),
            "next_event": st.get("next_event"),
            "seconds_to_next_event": st.get("seconds_to_next_event"),
        })

    return Response(debug_info)


@api_view(["POST", "GET"])
@permission_classes([IsAdminUser])
def sync_markets(request):
    """
    Deprecated compatibility endpoint (admin-only).
    """
    return Response({"detail": "Deprecated: use control markets config / seed commands instead."})
