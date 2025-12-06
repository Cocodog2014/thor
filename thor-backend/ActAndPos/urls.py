from django.urls import path

from .views import activity_today_view, positions_view
from .views.accounts_list import accounts_list_view
from .views.paper_orders import paper_order_create_view, paper_order_cancel_view

app_name = "ActAndPos"

urlpatterns = [
    path("positions", positions_view, name="positions"),
    path("activity/today", activity_today_view, name="activity-today"),

    # NEW: accounts list (for dropdown)
    path("accounts", accounts_list_view, name="accounts-list"),

    # NEW: paper trading endpoints
    path("paper/orders", paper_order_create_view, name="paper-order-create"),
    path(
        "paper/orders/<int:pk>/cancel",
        paper_order_cancel_view,
        name="paper-order-cancel",
    ),
]
