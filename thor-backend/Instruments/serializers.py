from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from Instruments.models import Instrument, UserInstrumentWatchlistItem
from LiveData.schwab.signal_control import suppress_schwab_subscription_signals


class InstrumentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = (
            "id",
            "symbol",
            "asset_type",
            "name",
            "exchange",
            "currency",
            "is_active",
        )


class WatchlistItemSerializer(serializers.ModelSerializer):
    instrument = InstrumentSummarySerializer(read_only=True)

    class Meta:
        model = UserInstrumentWatchlistItem
        fields = (
            "instrument",
            "enabled",
            "stream",
            "order",
        )


class WatchlistItemUpsertSerializer(serializers.Serializer):
    instrument_id = serializers.IntegerField(required=False)
    symbol = serializers.CharField(required=False)

    enabled = serializers.BooleanField(required=False, default=True)
    stream = serializers.BooleanField(required=False, default=True)
    order = serializers.IntegerField(required=False, default=0)

    def validate(self, attrs):
        if not attrs.get("instrument_id") and not attrs.get("symbol"):
            raise serializers.ValidationError("Provide instrument_id or symbol")
        return attrs


class WatchlistReplaceSerializer(serializers.Serializer):
    items = WatchlistItemUpsertSerializer(many=True)

    def save(self, **kwargs):
        request = self.context.get("request")
        if request is None or not getattr(request, "user", None) or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        user = request.user
        items = self.validated_data.get("items") or []

        # Resolve instruments
        resolved: list[tuple[Instrument, dict]] = []
        for item in items:
            instrument = None
            if item.get("instrument_id"):
                instrument = Instrument.objects.filter(id=item["instrument_id"]).first()
            elif item.get("symbol"):
                raw_symbol = str(item["symbol"]).strip().upper()
                canonical_symbol = raw_symbol.lstrip("/")

                instrument = Instrument.objects.filter(symbol__iexact=canonical_symbol).first()
                if instrument is None and raw_symbol.startswith("/"):
                    # Back-compat: tolerate legacy Instrument symbols that include '/'.
                    instrument = Instrument.objects.filter(symbol__iexact=raw_symbol).first()

                if instrument is None and canonical_symbol:
                    inferred_asset_type = (
                        Instrument.AssetType.FUTURE
                        if raw_symbol.startswith("/")
                        else Instrument.AssetType.EQUITY
                    )
                    instrument, _created = Instrument.objects.get_or_create(
                        symbol=canonical_symbol,
                        defaults={
                            "asset_type": inferred_asset_type,
                            "is_active": True,
                        },
                    )
            if instrument is None:
                raise serializers.ValidationError(f"Unknown instrument: {item.get('instrument_id') or item.get('symbol')}")
            resolved.append((instrument, item))

        # This serializer is used by the API "replace watchlist" path.
        # Keep signals suppressed during the bulk write to avoid per-row control-plane spam.
        with suppress_schwab_subscription_signals(), transaction.atomic():
            keep_ids = {inst.id for inst, _ in resolved}
            UserInstrumentWatchlistItem.objects.filter(user=user).exclude(instrument_id__in=keep_ids).delete()

            for inst, payload in resolved:
                UserInstrumentWatchlistItem.objects.update_or_create(
                    user=user,
                    instrument=inst,
                    defaults={
                        "enabled": bool(payload.get("enabled", True)),
                        "stream": bool(payload.get("stream", True)),
                        "order": int(payload.get("order", 0)),
                    },
                )

        return True
