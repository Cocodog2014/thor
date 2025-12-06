from django.urls import path

from .views.paper_orders import (
    paper_order_view,
    paper_order_create_view,
    paper_order_cancel_view,
)

app_name = "Trades"

urlpatterns = [
    path("paper/order", paper_order_view, name="paper-order"),
    path("paper/orders", paper_order_create_view, name="paper-orders-create"),
    path("paper/orders/<int:pk>/cancel", paper_order_cancel_view, name="paper-orders-cancel"),
]
