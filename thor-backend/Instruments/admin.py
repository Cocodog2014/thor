from django.contrib import admin
from django.db import transaction

from .models import Instrument
from .models import UserInstrumentWatchlistItem
from Instruments.services.watchlist_sync import sync_watchlist_to_schwab


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "asset_type", "exchange", "is_active", "updated_at")
    list_filter = ("asset_type", "exchange", "is_active")
    search_fields = ("symbol", "name", "exchange")

    def _sync_users_for_instrument(self, instrument: Instrument) -> None:
        user_ids = (
            UserInstrumentWatchlistItem.objects.filter(instrument=instrument)
            .values_list("user_id", flat=True)
            .distinct()
        )

        def _on_commit() -> None:
            for user_id in user_ids:
                sync_watchlist_to_schwab(int(user_id))

        transaction.on_commit(_on_commit)

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        super().save_model(request, obj, form, change)
        self._sync_users_for_instrument(obj)

    def delete_model(self, request, obj):  # pragma: no cover - admin
        # Capture affected users before delete.
        user_ids = (
            UserInstrumentWatchlistItem.objects.filter(instrument=obj)
            .values_list("user_id", flat=True)
            .distinct()
        )
        super().delete_model(request, obj)

        def _on_commit() -> None:
            for user_id in user_ids:
                sync_watchlist_to_schwab(int(user_id))

        transaction.on_commit(_on_commit)


@admin.register(UserInstrumentWatchlistItem)
class UserInstrumentWatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "instrument", "enabled", "stream", "order", "updated_at")
    list_filter = ("enabled", "stream", "instrument__asset_type")
    search_fields = ("user__email", "instrument__symbol", "instrument__name")

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        super().save_model(request, obj, form, change)
        transaction.on_commit(lambda: sync_watchlist_to_schwab(int(obj.user_id)))

    def delete_model(self, request, obj):  # pragma: no cover - admin
        user_id = int(obj.user_id)
        super().delete_model(request, obj)
        transaction.on_commit(lambda: sync_watchlist_to_schwab(user_id))
