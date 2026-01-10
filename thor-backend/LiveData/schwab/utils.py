from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import AnonymousUser

from LiveData.schwab.models import BrokerConnection


def get_schwab_connection(user) -> Optional[BrokerConnection]:
    """Return the user's Schwab BrokerConnection (may be expired)."""

    if not user or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return None

    getter = getattr(user, "get_broker_connection", None)
    if callable(getter):
        conn = getter(BrokerConnection.BROKER_SCHWAB) or getter("SCHWAB")
        if conn:
            return conn

    conn = getattr(user, "schwab_token", None)
    if isinstance(conn, BrokerConnection) or conn is None:
        return conn

    try:
        return BrokerConnection.objects.filter(user=user, broker=BrokerConnection.BROKER_SCHWAB).first()
    except Exception:
        return None


def get_active_schwab_connection(user) -> Optional[BrokerConnection]:
    """Return the user's Schwab BrokerConnection if present and not expired."""

    getter = getattr(user, "get_active_schwab_token", None)
    if callable(getter):
        return getter()

    conn = get_schwab_connection(user)
    if not conn:
        return None

    if getattr(conn, "is_expired", False):
        return None

    return conn
