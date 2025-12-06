from django.contrib import admin

from .models import Trade


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
