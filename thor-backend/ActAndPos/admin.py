from django.contrib import admin

from .models import Account, AccountDailySnapshot, Order, Position


class PositionInline(admin.TabularInline):
	model = Position
	extra = 0
	readonly_fields = ("updated_at", "market_value", "unrealized_pl", "pl_percent")


class OrderInline(admin.TabularInline):
	model = Order
	extra = 0
	readonly_fields = ("time_last_update", "time_filled", "time_canceled")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
	list_display = (
		"display_name",
		"user",
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
	list_filter = ("user", "broker", "currency")
	search_fields = ("display_name", "broker_account_id")
	ordering = ("-updated_at",)
	readonly_fields = ("updated_at",)
	inlines = [PositionInline, OrderInline]
	fieldsets = (
		(
			"Account",
			{
				"fields": (
					"display_name",
					"broker",
					"broker_account_id",
					"currency",
					"starting_balance",
					"net_liq",
					"cash",
					"current_cash",
					"equity",
					"stock_buying_power",
					"option_buying_power",
					"day_trading_buying_power",
					"updated_at",
				),
			},
		),
		(
			"Per-Order Commissions",
			{"fields": ("commission_scheme", "commission_flat_rate", "commission_percent_rate", "trade_fee_flat")},
		),
		(
			"Monthly Billing",
			{"fields": ("billing_plan", "billing_flat_monthly", "billing_performance_pct")},
		),
	)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
	list_display = (
		"account",
		"account_user",
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
	list_filter = ("account__user", "asset_type", "currency", "account")
	search_fields = (
		"symbol",
		"description",
		"account__display_name",
		"account__broker_account_id",
		"account__user__email",
	)
	ordering = ("account", "symbol")
	readonly_fields = ("updated_at", "market_value", "unrealized_pl", "pl_percent")

	def account_user(self, obj):
		return obj.account.user

	account_user.short_description = "User"
	account_user.admin_order_field = "account__user"


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


@admin.register(AccountDailySnapshot)
class AccountDailySnapshotAdmin(admin.ModelAdmin):
	list_display = (
		"account",
		"trading_date",
		"net_liq",
		"cash",
		"equity",
		"stock_buying_power",
		"captured_at",
	)
	list_filter = ("trading_date", "account", "account__user", "account__broker")
	search_fields = (
		"account__display_name",
		"account__broker_account_id",
		"account__user__email",
	)
	ordering = ("-trading_date", "-captured_at")
	date_hierarchy = "trading_date"
	list_select_related = ("account",)
