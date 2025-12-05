from django.contrib import admin

from .models import Account, Order, Position, Trade


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
	list_display = (
		"display_name",
		"broker",
		"broker_account_id",
		"currency",
		"net_liq",
		"cash",
		"stock_buying_power",
		"option_buying_power",
		"day_trading_buying_power",
		"ok_to_trade",
		"updated_at",
	)
	list_filter = ("broker", "currency")
	search_fields = ("display_name", "broker_account_id")
	ordering = ("-updated_at",)
	readonly_fields = ("updated_at",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
	list_display = (
		"account",
		"symbol",
		"description",
		"asset_type",
		"quantity",
		"avg_price",
		"mark_price",
		"market_value",
		"unrealized_pl",
		"pl_percent",
		"currency",
		"updated_at",
	)
	list_filter = ("asset_type", "currency", "account")
	search_fields = ("symbol", "description", "account__display_name", "account__broker_account_id")
	ordering = ("account", "symbol")
	readonly_fields = ("updated_at", "market_value", "unrealized_pl", "pl_percent")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = (
		"account",
		"symbol",
		"asset_type",
		"side",
		"quantity",
		"order_type",
		"limit_price",
		"stop_price",
		"status",
		"time_placed",
		"time_last_update",
		"time_filled",
		"time_canceled",
	)
	list_filter = ("status", "side", "order_type", "asset_type", "account")
	search_fields = ("symbol", "account__display_name", "account__broker_account_id", "broker_order_id")
	date_hierarchy = "time_placed"
	ordering = ("-time_placed",)
	list_select_related = ("account",)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
	list_display = (
		"account",
		"order",
		"symbol",
		"side",
		"quantity",
		"price",
		"commission",
		"fees",
		"exec_time",
	)
	list_filter = ("side", "account")
	search_fields = (
		"symbol",
		"account__display_name",
		"account__broker_account_id",
		"exec_id",
		"order__broker_order_id",
	)
	date_hierarchy = "exec_time"
	ordering = ("-exec_time",)
	list_select_related = ("account", "order")
