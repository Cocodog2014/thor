from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from Instruments.models import Instrument, UserInstrumentWatchlistItem
from Instruments.serializers import InstrumentSummarySerializer, WatchlistItemSerializer, WatchlistReplaceSerializer
from Instruments.services.watchlist_sync import sync_watchlist_to_schwab
from Instruments.services.watchlist_redis_sets import sync_watchlist_sets_to_redis
from Instruments.services.watchlist_redis_sets import set_watchlist_order_in_redis
from ActAndPos.live.models import LiveBalance

User = get_user_model()


class UserWatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def _resolve_mode(self, request) -> str:
        """Resolve watchlist mode from query params, defaulting sensibly."""

        mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
        paper = getattr(mode_cls, "PAPER", "PAPER")
        live = getattr(mode_cls, "LIVE", "LIVE")

        raw = (request.query_params.get("mode") or "").strip().lower()
        if raw in {"paper", "p"}:
            return paper
        if raw in {"live", "l"}:
            return live

        # Back-compat: if mode not supplied, infer based on whether the user has any live balances.
        has_live = LiveBalance.objects.filter(user=request.user).exists()
        return live if has_live else paper

    def get(self, request):
        mode = self._resolve_mode(request)
        items = UserInstrumentWatchlistItem.objects.select_related("instrument").filter(user=request.user, mode=mode)

        items = items.order_by("order", "instrument__symbol")
        return Response({"items": WatchlistItemSerializer(items, many=True).data})

    def put(self, request):
        mode = self._resolve_mode(request)
        serializer = WatchlistReplaceSerializer(data=request.data, context={"request": request, "mode": mode})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Mirror watchlist membership into Redis so UI rendering can avoid DB reads.
        sync_watchlist_sets_to_redis(int(request.user.id))

        # PAPER and LIVE both drive Schwab streaming subscriptions (union).
        sync_watchlist_to_schwab(int(request.user.id))

        items = (
            UserInstrumentWatchlistItem.objects.select_related("instrument")
            .filter(user=request.user, mode=mode)
            .order_by("order", "instrument__symbol")
        )
        return Response({"items": WatchlistItemSerializer(items, many=True).data})


class InstrumentCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        asset_type = (request.query_params.get("asset_type") or "").strip().upper()

        qs = Instrument.objects.filter(is_active=True)

        if asset_type:
            valid_asset_types = {c[0] for c in Instrument.AssetType.choices}
            if asset_type not in valid_asset_types:
                return Response(
                    {
                        "detail": "Invalid asset_type",
                        "valid": sorted(valid_asset_types),
                    },
                    status=400,
                )
            qs = qs.filter(asset_type=asset_type)

        if q:
            qs = qs.filter(Q(symbol__istartswith=q) | Q(name__icontains=q))

        # Keep payload small; this endpoint is intended for dropdown autocomplete.
        items = qs.order_by("symbol")[:50]
        return Response({"items": InstrumentSummarySerializer(items, many=True).data})


class UserWatchlistOrderView(APIView):
    """Persist drag/drop ordering to Redis (no DB writes).

    POST body:
      {"symbols": ["/ES", "AAPL", ...]}

    Query params:
      - mode: live|paper (required; avoids DB lookups for default inference)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_mode = (request.query_params.get("mode") or "").strip().lower()
        if raw_mode not in {"live", "paper"}:
            return Response(
                {"detail": "mode is required", "valid": ["live", "paper"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        symbols = request.data.get("symbols")
        if symbols is None:
            return Response(
                {"detail": "symbols is required", "example": {"symbols": ["/ES", "AAPL"]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(symbols, list):
            return Response(
                {"detail": "symbols must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = set_watchlist_order_in_redis(user_id=int(request.user.id), mode=raw_mode, symbols=symbols)
            return Response({**result, "source": "redis_watchlist_order"}, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": "Failed to update Redis watchlist order", "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
