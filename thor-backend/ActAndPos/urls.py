# ActAndPos/urls.py
from django.urls import path

from .views.account_orders import activity_today_view
from .views.positions import positions_view
from .views.accounts import account_summary_view
from .views.accounts_list import accounts_list_view

app_name = "ActAndPos"

urlpatterns = [
    # Existing endpoints
    path("positions", positions_view, name="positions"),
    path("activity/today", activity_today_view, name="activity-today"),

    # 🔹 New: single-account summary (for pages that show one account)
    path("account", account_summary_view, name="account-summary"),

    # 🔹 New: list of all accounts (used by GlobalBanner dropdown)
    path("accounts", accounts_list_view, name="accounts-list"),
]

