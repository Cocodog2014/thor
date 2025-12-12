from django.contrib import admin

from .models import BrokerConnection


@admin.register(BrokerConnection)
class BrokerConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "broker",
        "broker_account_id",
        "trading_enabled",
        "updated_at",
    )
    list_editable = ("trading_enabled",)
    list_filter = ("broker", "trading_enabled", "updated_at")
    search_fields = ("user__email", "broker_account_id")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "access_expires_at")
    fieldsets = (
        (
            "Connection",
            {
                "fields": (
                    "user",
                    "broker",
                    "broker_account_id",
                    "trading_enabled",
                )
            },
        ),
        (
            "Tokens",
            {
                "fields": (
                    "access_token",
                    "refresh_token",
                    "access_expires_at",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )
