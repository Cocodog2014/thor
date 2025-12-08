from django.urls import path

from .views.paper_orders import (
    order_create_active_view,
    order_create_view,
    order_cancel_view,
)
from .views.statements import account_statement_view

app_name = "Trades"

urlpatterns = [
    # Create an order for the *active* account (from session / ?account_id=)
    path("orders/active", order_create_active_view, name="orders-create-active"),

    # Create an order for a specific account_id in the payload
    path("orders", order_create_view, name="orders-create"),

    # Cancel an existing WORKING order
    path("orders/<int:pk>/cancel", order_cancel_view, name="orders-cancel"),

    # Account statement / report
    path("account-statement", account_statement_view, name="account-statement"),
]

