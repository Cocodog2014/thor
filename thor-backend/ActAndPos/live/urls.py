from django.urls import path

from .views import (
    live_accounts_view,
    live_balances_view,
    live_orders_submit_view,
    live_orders_view,
    live_positions_view,
    live_refresh_view,
)


urlpatterns = [
    path("accounts", live_accounts_view, name="actandpos-live-accounts"),
    path("balances", live_balances_view, name="actandpos-live-balances"),
    path("positions", live_positions_view, name="actandpos-live-positions"),
    path("orders", live_orders_view, name="actandpos-live-orders"),
    path("orders/submit", live_orders_submit_view, name="actandpos-live-orders-submit"),
    path("refresh", live_refresh_view, name="actandpos-live-refresh"),
]
