from django.contrib import admin

from .models import Market, MarketSession, MarketHoliday


class MarketSessionInline(admin.TabularInline):
    model = MarketSession
    extra = 0
    fields = (
        "weekday",
        "is_closed",
        "premarket_open_time",
        "open_time",
        "close_time",
    )
    ordering = ("weekday",)


class MarketHolidayInline(admin.TabularInline):
    model = MarketHoliday
    extra = 0
    fields = ("date", "name", "is_closed", "early_close_time")
    ordering = ("-date",)


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = (
        "sort_order",
        "key",
        "name",
        "timezone_name",
        "is_active",
        "status",
        "status_changed_at",
    )
    list_editable = ("sort_order", "is_active")
    search_fields = ("key", "name", "timezone_name")
    list_filter = ("is_active", "status", "timezone_name")
    ordering = ("sort_order", "name")

    inlines = [MarketSessionInline, MarketHolidayInline]

