from django.contrib import admin

from .models import Market, MarketHoliday


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
    
    # Sessions removed - not needed for simple Monday-Friday schedules
    # Markets automatically trade Monday-Friday using open_time/close_time
    # Weekends (Sat/Sun) are automatically closed


@admin.register(MarketHoliday)
class MarketHolidayAdmin(admin.ModelAdmin):
    """US Market Holidays that apply to all markets"""
    list_display = ("date", "name", "is_closed", "early_close_time")
    list_filter = ("is_closed",)
    search_fields = ("name",)
    ordering = ("-date",)


