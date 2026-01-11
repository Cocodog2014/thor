from django.urls import path

from .views import (
    paper_accounts_view,
    paper_balances_view,
    paper_orders_submit_view,
    paper_orders_view,
    paper_positions_view,
)


urlpatterns = [
    path("accounts", paper_accounts_view, name="actandpos-paper-accounts"),
    path("balances", paper_balances_view, name="actandpos-paper-balances"),
    path("positions", paper_positions_view, name="actandpos-paper-positions"),
    path("orders", paper_orders_view, name="actandpos-paper-orders"),
    path("orders/submit", paper_orders_submit_view, name="actandpos-paper-orders-submit"),
]
