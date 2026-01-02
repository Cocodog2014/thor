from django.contrib import admin

from .models import Instrument
from .models import UserInstrumentWatchlistItem


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("symbol", "asset_type", "exchange", "is_active", "updated_at")
    list_filter = ("asset_type", "exchange", "is_active")
    search_fields = ("symbol", "name", "exchange")


@admin.register(UserInstrumentWatchlistItem)
class UserInstrumentWatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "instrument", "enabled", "stream", "order", "updated_at")
    list_filter = ("enabled", "stream", "instrument__asset_type")
    search_fields = ("user__email", "instrument__symbol", "instrument__name")
