from django.contrib import admin
from django.db import transaction

from LiveData.schwab.signal_control import suppress_schwab_subscription_signals

from .models import Instrument
from .models import InstrumentIntraday
from .models import MarketTrading24Hour
from .models import Rolling52WeekStats
from .models import UserInstrumentWatchlistItem
from Instruments.services.watchlist_sync import sync_watchlist_to_schwab, sync_global_watchlist_to_schwab
from Instruments.services.instrument_sync import (
    remove_owner_watchlist_for_instrument,
    upsert_quote_source_map,
    remove_quote_source_map,
    get_owner_user_id,
)


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "asset_type", "quote_source", "exchange", "is_active", "updated_at")
    list_filter = ("asset_type", "exchange", "is_active")
    search_fields = ("symbol", "name", "exchange")

    def _sync_users_for_instrument(self, instrument: Instrument) -> None:
        mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
        live = getattr(mode_cls, "LIVE", "LIVE")
        global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")

        user_ids = list(
            UserInstrumentWatchlistItem.objects.filter(instrument=instrument, mode__in=[live, global_mode])
            .values_list("user_id", flat=True)
            .distinct()
        )

        def _on_commit() -> None:
            for user_id in user_ids:
                sync_watchlist_to_schwab(int(user_id), publish_on_commit=False)

        transaction.on_commit(_on_commit)

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        super().save_model(request, obj, form, change)

        # Publish per-symbol quote source preference for fast gating.
        upsert_quote_source_map(obj)

        self._sync_users_for_instrument(obj)

    def delete_model(self, request, obj):  # pragma: no cover - admin
        # Capture affected users before delete.
        user_ids = list(
            UserInstrumentWatchlistItem.objects.filter(instrument=obj)
            .values_list("user_id", flat=True)
            .distinct()
        )
        symbol = obj.symbol
        instrument_id = obj.id

        # Remove from owner watchlist before the instrument row is deleted.
        if instrument_id is not None:
            remove_owner_watchlist_for_instrument(int(instrument_id))
        super().delete_model(request, obj)

        # Remove from source map.
        remove_quote_source_map(symbol)

        def _on_commit() -> None:
            for user_id in user_ids:
                sync_watchlist_to_schwab(int(user_id), publish_on_commit=False)

        transaction.on_commit(_on_commit)

    def delete_queryset(self, request, queryset):  # pragma: no cover - admin
        # Bulk delete path ("delete selected") does NOT call delete_model.
        symbols = list(queryset.values_list("symbol", flat=True))
        instrument_ids = list(queryset.values_list("id", flat=True))
        user_ids = list(
            UserInstrumentWatchlistItem.objects.filter(instrument_id__in=instrument_ids)
            .values_list("user_id", flat=True)
            .distinct()
        )

        # If signals are ever enabled, bulk deletes could otherwise trigger per-row publish spam
        # (including cascaded deletes). Suppress during the delete, then publish one authoritative
        # sync per affected user on commit.
        with suppress_schwab_subscription_signals():
            # Remove from owner watchlist before deletion (cascades will handle the rest).
            if instrument_ids:
                owner_user_id = get_owner_user_id()
                mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
                global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")
                UserInstrumentWatchlistItem.objects.filter(
                    user_id=int(owner_user_id),
                    instrument_id__in=instrument_ids,
                    mode=global_mode,
                ).delete()

            super().delete_queryset(request, queryset)

        def _on_commit() -> None:
            for sym in symbols:
                remove_quote_source_map(sym)
            for user_id in user_ids:
                sync_watchlist_to_schwab(int(user_id), publish_on_commit=False)

        transaction.on_commit(_on_commit)


@admin.register(UserInstrumentWatchlistItem)
class UserInstrumentWatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "instrument", "enabled", "stream", "order", "updated_at")
    list_filter = ("mode", "enabled", "stream", "instrument__asset_type")
    search_fields = ("user__email", "instrument__symbol", "instrument__name")

    def get_changeform_initial_data(self, request):  # pragma: no cover - admin
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("user", request.user.id)
        return initial

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        if not getattr(obj, "user_id", None):
            obj.user = request.user
        with suppress_schwab_subscription_signals():
            super().save_model(request, obj, form, change)

        mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
        live = getattr(mode_cls, "LIVE", "LIVE")
        global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")
        if getattr(obj, "mode", None) == global_mode:
            transaction.on_commit(lambda: sync_global_watchlist_to_schwab(publish_on_commit=False))
        elif getattr(obj, "mode", None) == live:
            transaction.on_commit(lambda: sync_watchlist_to_schwab(int(obj.user_id), publish_on_commit=False))

    def delete_model(self, request, obj):  # pragma: no cover - admin
        user_id = int(obj.user_id)
        with suppress_schwab_subscription_signals():
            super().delete_model(request, obj)

        mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
        live = getattr(mode_cls, "LIVE", "LIVE")
        global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")
        if getattr(obj, "mode", None) == global_mode:
            transaction.on_commit(lambda: sync_global_watchlist_to_schwab(publish_on_commit=False))
        elif getattr(obj, "mode", None) == live:
            transaction.on_commit(lambda: sync_watchlist_to_schwab(user_id, publish_on_commit=False))


@admin.register(Rolling52WeekStats)
class Rolling52WeekStatsAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "high_52w",
        "high_52w_date",
        "low_52w",
        "low_52w_date",
        "last_price_checked",
        "stale_hours_display",
        "last_updated",
    ]
    list_filter = ["high_52w_date", "low_52w_date"]
    search_fields = ["symbol"]
    readonly_fields = ["last_price_checked", "last_updated", "created_at"]
    ordering = ["symbol"]

    fieldsets = (
        ("Symbol", {"fields": ("symbol",)}),
        (
            "52-Week High",
            {
                "fields": ("high_52w", "high_52w_date"),
                "description": "Enter initial 52-week high. System will auto-update when exceeded.",
            },
        ),
        (
            "52-Week Low",
            {
                "fields": ("low_52w", "low_52w_date"),
                "description": "Enter initial 52-week low. System will auto-update when breached.",
            },
        ),
        (
            "All-Time Extremes (Optional)",
            {
                "fields": ("all_time_high", "all_time_high_date", "all_time_low", "all_time_low_date"),
                "classes": ("collapse",),
                "description": "Leave blank to track automatically, or enter known values.",
            },
        ),
        (
            "System Tracking",
            {
                "fields": ("last_price_checked", "last_updated", "created_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        if not change:
            from django.utils import timezone

            today = timezone.localdate()
            if not obj.high_52w_date:
                obj.high_52w_date = today
            if not obj.low_52w_date:
                obj.low_52w_date = today
        super().save_model(request, obj, form, change)

    def stale_hours_display(self, obj):
        val = obj.stale_hours()
        return f"{val:.2f}" if val is not None else "-"

    stale_hours_display.short_description = "Stale (h)"


@admin.register(InstrumentIntraday)
class InstrumentIntradayAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp_minute",
        "symbol",
        "open_1m",
        "high_1m",
        "low_1m",
        "close_1m",
        "volume_1m",
        "bid_last",
        "ask_last",
        "spread_last",
    )
    list_filter = ("symbol",)
    search_fields = ("symbol",)
    ordering = ("-timestamp_minute", "symbol")
    date_hierarchy = "timestamp_minute"
    readonly_fields = ("timestamp_minute",)


@admin.register(MarketTrading24Hour)
class MarketTrading24HourAdmin(admin.ModelAdmin):
    list_display = (
        "session_number",
        "session_date",
        "symbol",
        "open_price_24h",
        "prev_close_24h",
        "low_24h",
        "high_24h",
        "range_diff_24h",
        "range_pct_24h",
        "close_24h",
        "finalized",
    )
    list_filter = (
        "session_date",
        "symbol",
        "finalized",
    )
    search_fields = (
        "symbol",
        "session_number",
    )
    ordering = ("-session_date", "symbol")
    date_hierarchy = "session_date"
    readonly_fields = ("finalized",)

    fields = (
        "session_number",
        "session_date",
        "symbol",
        "prev_close_24h",
        "open_prev_diff_24h",
        "open_prev_pct_24h",
        "open_price_24h",
        "low_24h",
        "high_24h",
        "range_diff_24h",
        "range_pct_24h",
        "close_24h",
        "volume_24h",
        "finalized",
    )
