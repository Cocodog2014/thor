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
from Instruments.services.watchlist_redis_sets import sync_watchlist_sets_to_redis, is_watchlists_hydrated
from Instruments.services.watchlist_redis_sets import set_watchlist_order_in_redis
from Instruments.services.watchlist_redis_sets import build_watchlist_items_payload, get_watchlists_snapshot_from_redis
from ActAndPos.live.models import LiveBalance

from api.websocket.broadcast import broadcast_to_websocket_sync

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

    def _mode_norm(self, mode: str) -> str:
        mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
        paper = getattr(mode_cls, "PAPER", "PAPER")
        live = getattr(mode_cls, "LIVE", "LIVE")
        return "paper" if mode == paper else ("live" if mode == live else "live")

    def _broadcast_watchlist_updated(self, *, user_id: int) -> None:
        try:
            snapshot = get_watchlists_snapshot_from_redis(user_id=int(user_id))
        except Exception:
            snapshot = {"paper": [], "live": []}

        # Send only to the authenticated user's private group.
        broadcast_to_websocket_sync(
            channel_layer=None,
            group_name=f"user:{int(user_id)}",
            message={
                "type": "watchlist_updated",
                "data": {
                    "user_id": int(user_id),
                    "watchlists": snapshot,
                },
            },
        )

    def get(self, request):
        mode = self._resolve_mode(request)
        mode_norm = self._mode_norm(mode)

        # Redis-first (runtime truth). DB is only used to hydrate Redis on cold cache.
        def _read_from_redis() -> list[dict] | None:
            return build_watchlist_items_payload(
                user_id=int(request.user.id),
                mode_norm=mode_norm,
                db_mode=mode,
            )

        try:
            redis_items = _read_from_redis()
        except Exception:
            redis_items = None

        if redis_items is None and not is_watchlists_hydrated(user_id=int(request.user.id)):
            # Cold cache: hydrate from DB into Redis, then re-read.
            sync_watchlist_sets_to_redis(int(request.user.id))
            try:
                redis_items = _read_from_redis()
            except Exception:
                redis_items = None

        # If still None, Redis is now the source of truth and the list is empty.
        if redis_items is None:
            redis_items = []

        return Response({"items": redis_items, "source": "redis"})

    def put(self, request):
        mode = self._resolve_mode(request)
        mode_norm = self._mode_norm(mode)
        serializer = WatchlistReplaceSerializer(data=request.data, context={"request": request, "mode": mode})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Mirror watchlist membership into Redis so UI rendering can avoid DB reads.
        sync_watchlist_sets_to_redis(int(request.user.id))

        # Notify UI instantly (no need to refetch from DB).
        try:
            self._broadcast_watchlist_updated(user_id=int(request.user.id))
        except Exception:
            pass

        # PAPER and LIVE both drive Schwab streaming subscriptions (union).
        sync_watchlist_to_schwab(int(request.user.id))

        # Respond from Redis (runtime truth); avoid DB read in the response.
        try:
            redis_items = build_watchlist_items_payload(
                user_id=int(request.user.id),
                mode_norm=mode_norm,
                db_mode=mode,
            )
        except Exception:
            redis_items = None

        return Response({"items": redis_items or [], "source": "redis"})


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

            # Notify UI instantly.
            try:
                snapshot = get_watchlists_snapshot_from_redis(user_id=int(request.user.id))
                broadcast_to_websocket_sync(
                    channel_layer=None,
                    group_name=f"user:{int(request.user.id)}",
                    message={
                        "type": "watchlist_updated",
                        "data": {
                            "user_id": int(request.user.id),
                            "watchlists": snapshot,
                        },
                    },
                )
            except Exception:
                pass

            return Response({**result, "source": "redis_watchlist_order"}, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": "Failed to update Redis watchlist order", "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
