from django.contrib import admin

from .models import Market, MarketHoliday
from .models.market_clock import MarketStatusEvent


class MarketStatusEventInline(admin.TabularInline):
    model = MarketStatusEvent
    extra = 0
    can_delete = False
    ordering = ("-changed_at",)
    fields = ("changed_at", "old_status", "new_status", "reason")
    readonly_fields = fields
    show_change_link = True


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
        ("Trading Hours (Monday-Friday)", {
            "fields": ("open_time", "close_time"),
            "description": "Trading hours in local time. Automatically applies Monday-Friday. Weekends are closed automatically."
        }),
        ("Status", {
            "fields": ("status", "status_changed_at"),
            "classes": ("collapse",)
        }),
    )

    # Show recent status transitions on the Market detail page
    inlines = [MarketStatusEventInline]


@admin.register(MarketStatusEvent)
class MarketStatusEventAdmin(admin.ModelAdmin):
    list_display = ("changed_at", "market", "old_status", "new_status", "reason")
    list_filter = ("market", "old_status", "new_status")
    search_fields = ("market__key", "market__name", "reason")
    date_hierarchy = "changed_at"
    ordering = ("-changed_at",)


@admin.register(MarketHoliday)
class MarketHolidayAdmin(admin.ModelAdmin):
    """US Market Holidays that apply to all markets"""
    list_display = ("date", "name", "is_closed", "early_close_time")
    list_filter = ("is_closed",)
    search_fields = ("name",)
    ordering = ("-date",)



