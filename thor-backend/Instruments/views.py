from __future__ import annotations

from django.db.models import Q
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from LiveData.schwab.models import SchwabSubscription
from Instruments.models import Instrument, UserInstrumentWatchlistItem
from Instruments.serializers import InstrumentSummarySerializer, WatchlistItemSerializer, WatchlistReplaceSerializer
from Instruments.services.watchlist_sync import sync_watchlist_to_schwab


class UserWatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = UserInstrumentWatchlistItem.objects.select_related("instrument").filter(user=request.user)

        # Back-compat: if a user already has SchwabSubscription rows (older flow),
        # seed the new watchlist once so the drawer reflects existing subscriptions.
        if not items.exists():
            subs = (
                SchwabSubscription.objects.filter(user=request.user, enabled=True)
                .order_by("asset_type", "symbol")
                .values_list("asset_type", "symbol")
            )

            to_create: list[UserInstrumentWatchlistItem] = []
            order = 0
            with transaction.atomic():
                for asset_type, symbol in subs:
                    sym = (symbol or "").strip().upper()
                    if not sym:
                        continue

                    inferred_asset_type = (
                        Instrument.AssetType.FUTURE
                        if asset_type == SchwabSubscription.ASSET_FUTURE or sym.startswith("/")
                        else Instrument.AssetType.EQUITY
                    )
                    inst, _ = Instrument.objects.get_or_create(
                        symbol=sym,
                        defaults={"asset_type": inferred_asset_type, "is_active": True},
                    )
                    to_create.append(
                        UserInstrumentWatchlistItem(
                            user=request.user,
                            instrument=inst,
                            enabled=True,
                            stream=True,
                            order=order,
                        )
                    )
                    order += 1

                if to_create:
                    UserInstrumentWatchlistItem.objects.bulk_create(
                        to_create,
                        ignore_conflicts=True,
                    )

            items = UserInstrumentWatchlistItem.objects.select_related("instrument").filter(user=request.user)

        items = items.order_by("order", "instrument__symbol")
        return Response({"items": WatchlistItemSerializer(items, many=True).data})

    def put(self, request):
        serializer = WatchlistReplaceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        sync_watchlist_to_schwab(int(request.user.id))

        items = (
            UserInstrumentWatchlistItem.objects.select_related("instrument")
            .filter(user=request.user)
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
