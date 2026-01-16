from __future__ import annotations

from django.db import transaction
from django.db.models import Exists, OuterRef
from rest_framework import serializers

from Instruments.models import Instrument, UserInstrumentWatchlistItem


class InstrumentSummarySerializer(serializers.ModelSerializer):
    symbol = serializers.SerializerMethodField()

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

    def get_symbol(self, obj: Instrument) -> str:
        sym = (getattr(obj, "symbol", None) or "").strip()
        if not sym:
            return ""
        if obj.asset_type == Instrument.AssetType.FUTURE:
            return sym if sym.startswith("/") else f"/{sym.lstrip('/')}"
        if obj.asset_type == Instrument.AssetType.INDEX:
            return sym if sym.startswith("$") else f"${sym.lstrip('$')}"
        return sym.lstrip("/")


class WatchlistItemSerializer(serializers.ModelSerializer):
    instrument = InstrumentSummarySerializer(read_only=True)

    class Meta:
        model = UserInstrumentWatchlistItem
        fields = (
            "instrument",
            "enabled",
            "stream",
            "mode",
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

    def _merge_legacy_instrument(self, legacy: Instrument, canonical: Instrument) -> Instrument:
        """Best-effort merge of a legacy Instrument row into its canonical replacement.

        This is used to resolve historical cases where FUTURE instruments were stored without
        a leading '/' (e.g. symbol='SI', asset_type='FUTURE') while a canonical FUTURE row
        exists (symbol='/SI').
        """

        if legacy.id == canonical.id:
            return canonical

        try:
            with transaction.atomic():
                # Handle watchlist unique constraint (user, instrument, mode).
                # If both legacy+canonical exist for the same user+mode, drop legacy.
                to_exists = UserInstrumentWatchlistItem.objects.filter(
                    instrument_id=canonical.id,
                    user_id=OuterRef("user_id"),
                    mode=OuterRef("mode"),
                )
                (
                    UserInstrumentWatchlistItem.objects.filter(instrument_id=legacy.id)
                    .annotate(_has_canonical=Exists(to_exists))
                    .filter(_has_canonical=True)
                    .delete()
                )
                UserInstrumentWatchlistItem.objects.filter(instrument_id=legacy.id).update(instrument_id=canonical.id)

                # If other apps still reference the legacy instrument, try to migrate them too.
                # If this fails (unique constraint collisions, etc), abort without deleting.
                try:
                    from django.apps import apps
                    from django.db import models as dj_models

                    for model in apps.get_models():
                        for field in getattr(model._meta, "fields", []):
                            if not isinstance(field, dj_models.ForeignKey):
                                continue
                            if field.remote_field.model is not Instrument:
                                continue
                            model.objects.filter(**{field.attname: legacy.id}).update(**{field.attname: canonical.id})
                except Exception:
                    return canonical

                legacy.delete()
                return canonical
        except Exception:
            return canonical

    def _ensure_future_symbol_prefixed(self, inst: Instrument, future_symbol: str) -> Instrument:
        """Keep FUTURE instruments stored with a leading '/' so they can coexist with equities.

        Back-compat: older rows may have FUTURE asset_type but symbol stored without '/'.
        """

        try:
            if inst.asset_type != Instrument.AssetType.FUTURE:
                return inst

            want = (future_symbol or "").strip().upper()
            if not want:
                return inst
            if not want.startswith("/"):
                want = "/" + want.lstrip("/")

            current = (inst.symbol or "").strip().upper()
            if current == want:
                return inst

            # If a canonical FUTURE instrument already exists for this symbol, merge legacy into it.
            canonical = Instrument.objects.filter(symbol__iexact=want, asset_type=Instrument.AssetType.FUTURE).first()
            if canonical is not None and canonical.id != inst.id and current.lstrip("/") == want.lstrip("/"):
                return self._merge_legacy_instrument(inst, canonical)

            # Only rename if it's the same base symbol and the target isn't taken.
            if current.lstrip("/") != want.lstrip("/"):
                return inst
            if Instrument.objects.filter(symbol__iexact=want).exclude(id=inst.id).exists():
                return inst

            inst.symbol = want
            inst.save(update_fields=["symbol", "updated_at"])
            return inst
        except Exception:
            # Never fail the whole request due to a best-effort symbol normalization.
            return inst

    def save(self, **kwargs):
        request = self.context.get("request")
        if request is None or not getattr(request, "user", None) or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        user = self.context.get("user") or request.user
        mode = self.context.get("mode")
        if not mode:
            mode = getattr(getattr(UserInstrumentWatchlistItem, "Mode", None), "LIVE", "LIVE")
        items = self.validated_data.get("items") or []

        # Resolve instruments
        resolved: list[tuple[Instrument, dict]] = []
        for item in items:
            instrument = None
            if item.get("instrument_id"):
                instrument = Instrument.objects.filter(id=item["instrument_id"]).first()
            elif item.get("symbol"):
                raw_symbol = str(item["symbol"]).strip().upper()
                # Prefix rules:
                #   /XYZ  => FUTURE XYZ
                #   $XYZ  => INDEX $XYZ
                #   XYZ   => EQUITY XYZ
                if raw_symbol.startswith("$"):
                    index_symbol = "$" + raw_symbol.lstrip("$")
                    if index_symbol == "$":
                        raise serializers.ValidationError("Invalid symbol")
                    instrument = Instrument.objects.filter(
                        symbol__iexact=index_symbol,
                        asset_type=Instrument.AssetType.INDEX,
                    ).first()
                    if instrument is None:
                        # Avoid binding to a non-index row that happens to share the symbol.
                        if Instrument.objects.filter(symbol__iexact=index_symbol).exclude(asset_type=Instrument.AssetType.INDEX).exists():
                            raise serializers.ValidationError(f"Symbol {index_symbol} exists as non-index")
                        instrument, _created = Instrument.objects.get_or_create(
                            symbol=index_symbol,
                            defaults={
                                "asset_type": Instrument.AssetType.INDEX,
                                "is_active": True,
                            },
                        )
                    # Done: index
                    resolved.append((instrument, item))
                    continue

                canonical_symbol = raw_symbol.lstrip("/")

                if not canonical_symbol:
                    raise serializers.ValidationError("Invalid symbol")

                wants_future = raw_symbol.startswith("/")
                equity_symbol = canonical_symbol
                future_symbol = "/" + canonical_symbol

                if wants_future:
                    # Prefer an explicit future instrument stored with leading '/'.
                    instrument = Instrument.objects.filter(symbol__iexact=future_symbol).first()

                    # Back-compat: tolerate legacy FUTURE instruments stored without '/'.
                    if instrument is None:
                        instrument = Instrument.objects.filter(
                            symbol__iexact=equity_symbol,
                            asset_type=Instrument.AssetType.FUTURE,
                        ).first()
                        if instrument is not None:
                            instrument = self._ensure_future_symbol_prefixed(instrument, future_symbol)

                    if instrument is None:
                        instrument, _created = Instrument.objects.get_or_create(
                            symbol=future_symbol,
                            defaults={
                                "asset_type": Instrument.AssetType.FUTURE,
                                "is_active": True,
                            },
                        )
                else:
                    # Equities should never bind to a FUTURE instrument.
                    instrument = (
                        Instrument.objects.filter(symbol__iexact=equity_symbol)
                        .exclude(asset_type=Instrument.AssetType.FUTURE)
                        .first()
                    )

                    # If a legacy FUTURE instrument is squatting on the equity symbol (e.g. ES),
                    # try to migrate it to /ES so ES can be created as an equity.
                    if instrument is None:
                        legacy_future = Instrument.objects.filter(
                            symbol__iexact=equity_symbol,
                            asset_type=Instrument.AssetType.FUTURE,
                        ).first()
                        if legacy_future is not None:
                            self._ensure_future_symbol_prefixed(legacy_future, future_symbol)

                    instrument = (
                        Instrument.objects.filter(symbol__iexact=equity_symbol)
                        .exclude(asset_type=Instrument.AssetType.FUTURE)
                        .first()
                    )

                    if instrument is None:
                        # Create an equity row. If the symbol is still occupied by a FUTURE row,
                        # do not silently bind to it.
                        try:
                            instrument = Instrument.objects.create(
                                symbol=equity_symbol,
                                asset_type=Instrument.AssetType.EQUITY,
                                is_active=True,
                            )
                        except Exception:
                            existing = Instrument.objects.filter(symbol__iexact=equity_symbol).first()
                            if existing is not None and existing.asset_type == Instrument.AssetType.FUTURE:
                                raise serializers.ValidationError(
                                    f"Symbol {equity_symbol} is currently occupied by a FUTURE instrument; "
                                    "normalize futures to '/SYMBOL' first"
                                )
                            instrument = existing
            if instrument is None:
                raise serializers.ValidationError(f"Unknown instrument: {item.get('instrument_id') or item.get('symbol')}")
            resolved.append((instrument, item))

        # This serializer is used by the API "replace watchlist" path.
        with transaction.atomic():
            keep_ids = {inst.id for inst, _ in resolved}
            UserInstrumentWatchlistItem.objects.filter(user=user, mode=mode).exclude(instrument_id__in=keep_ids).delete()

            for inst, payload in resolved:
                UserInstrumentWatchlistItem.objects.update_or_create(
                    user=user,
                    instrument=inst,
                    mode=mode,
                    defaults={
                        "enabled": bool(payload.get("enabled", True)),
                        "stream": bool(payload.get("stream", True)),
                        "order": int(payload.get("order", 0)),
                    },
                )

        return True
