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


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = (
        "sort_order",
        "key",
        "name",
        "timezone_name",
        "open_time",
        "close_time",
        "is_active",
        "status",
        "status_changed_at",
    )
    list_display_links = ("key", "name")
    list_editable = ("sort_order", "is_active")
    search_fields = ("key", "name", "timezone_name")
    list_filter = ("is_active", "status", "timezone_name")
    ordering = ("sort_order", "name")
    fieldsets = (
        (None, {
            "fields": ("key", "name", "timezone_name", "sort_order", "is_active")
        }),
        ("Trading Hours", {
            "fields": ("open_time", "close_time"),
            "description": "Default trading hours (local time). Sessions can override for specific weekdays."
        }),
        ("Status", {
            "fields": ("status", "status_changed_at"),
            "classes": ("collapse",)
        }),
    )

    inlines = [MarketSessionInline]


@admin.register(MarketHoliday)
class MarketHolidayAdmin(admin.ModelAdmin):
    """US Market Holidays that apply to all markets"""
    list_display = ("date", "name", "is_closed", "early_close_time")
    list_filter = ("is_closed",)
    search_fields = ("name",)
    ordering = ("-date",)


