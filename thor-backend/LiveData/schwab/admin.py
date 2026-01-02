from django.contrib import admin
from django.contrib import messages

from .models import BrokerConnection, SchwabSubscription
from LiveData.schwab.client.tokens import ensure_valid_access_token


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

    actions = ["refresh_access_tokens"]

    def get_changeform_initial_data(self, request):  # pragma: no cover - admin
        initial = super().get_changeform_initial_data(request)
        # Convenience: default to the currently logged-in admin user.
        initial.setdefault("user", request.user.id)
        return initial

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        if not getattr(obj, "user_id", None):
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def refresh_access_tokens(self, request, queryset):
        """Admin action to force-refresh selected Schwab access tokens."""
        refreshed = 0
        errors = 0
        for connection in queryset:
            try:
                ensure_valid_access_token(connection, force_refresh=True)
                refreshed += 1
            except Exception as exc:  # pragma: no cover - admin utility
                errors += 1
                self.message_user(
                    request,
                    f"Failed to refresh Schwab token for user {connection.user_id}: {exc}",
                    level=messages.ERROR,
                )
        if refreshed:
            self.message_user(
                request,
                f"Refreshed Schwab tokens for {refreshed} connection(s)",
                level=messages.SUCCESS,
            )
        if not refreshed and not errors:
            self.message_user(request, "No connections selected for refresh", level=messages.INFO)

    refresh_access_tokens.short_description = "Force refresh Schwab token"


@admin.register(SchwabSubscription)
class SchwabSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "symbol", "asset_type", "enabled", "updated_at")
    list_editable = ("enabled",)
    list_filter = ("asset_type", "enabled", "updated_at")
    search_fields = ("user__email", "symbol")
    ordering = ("user", "asset_type", "symbol")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Subscription", {"fields": ("user", "symbol", "asset_type", "enabled")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_changeform_initial_data(self, request):  # pragma: no cover - admin
        initial = super().get_changeform_initial_data(request)
        # Convenience: default to the currently logged-in admin user.
        initial.setdefault("user", request.user.id)
        return initial

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin
        if not getattr(obj, "user_id", None):
            obj.user = request.user
        super().save_model(request, obj, form, change)

