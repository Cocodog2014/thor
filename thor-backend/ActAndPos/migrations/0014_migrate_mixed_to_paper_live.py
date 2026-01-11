from __future__ import annotations

from django.db import migrations


def _account_key(account) -> str:
    # Prefer the stable broker_account_id; fall back defensively.
    key = getattr(account, "broker_account_id", None) or getattr(account, "account_number", None)
    return str(key or getattr(account, "pk", ""))


def forwards(apps, schema_editor):
    Account = apps.get_model("ActAndPos", "Account")
    Position = apps.get_model("ActAndPos", "Position")
    Order = apps.get_model("ActAndPos", "Order")

    PaperBalance = apps.get_model("ActAndPos", "PaperBalance")
    PaperPosition = apps.get_model("ActAndPos", "PaperPosition")
    PaperOrder = apps.get_model("ActAndPos", "PaperOrder")

    LiveBalance = apps.get_model("ActAndPos", "LiveBalance")
    LivePosition = apps.get_model("ActAndPos", "LivePosition")
    LiveOrder = apps.get_model("ActAndPos", "LiveOrder")

    db = schema_editor.connection.alias

    # --- Balances (from Account row) ----------------------------------------
    paper_balances = []
    live_balances = []

    for account in Account.objects.using(db).all().iterator(chunk_size=2000):
        broker = (getattr(account, "broker", "") or "").upper()
        key = _account_key(account)

        if broker == "PAPER":
            paper_balances.append(
                PaperBalance(
                    user_id=getattr(account, "user_id", None),
                    account_key=key,
                    currency=getattr(account, "currency", "USD") or "USD",
                    cash=getattr(account, "cash", 0) or 0,
                    equity=getattr(account, "equity", 0) or 0,
                    net_liq=getattr(account, "net_liq", 0) or 0,
                    buying_power=getattr(account, "stock_buying_power", 0) or 0,
                    day_trade_bp=getattr(account, "day_trading_buying_power", 0) or 0,
                )
            )

        elif broker == "SCHWAB":
            live_balances.append(
                LiveBalance(
                    user_id=getattr(account, "user_id", None),
                    broker="SCHWAB",
                    broker_account_id=key,
                    currency=getattr(account, "currency", "USD") or "USD",
                    net_liq=getattr(account, "net_liq", 0) or 0,
                    cash=getattr(account, "cash", 0) or 0,
                    equity=getattr(account, "equity", 0) or 0,
                    stock_buying_power=getattr(account, "stock_buying_power", 0) or 0,
                    option_buying_power=getattr(account, "option_buying_power", 0) or 0,
                    day_trading_buying_power=getattr(account, "day_trading_buying_power", 0) or 0,
                    broker_payload=None,
                )
            )

    if paper_balances:
        PaperBalance.objects.using(db).bulk_create(paper_balances, ignore_conflicts=True, batch_size=2000)

    if live_balances:
        LiveBalance.objects.using(db).bulk_create(live_balances, ignore_conflicts=True, batch_size=2000)

    # --- Positions -----------------------------------------------------------
    paper_positions = []
    live_positions = []

    pos_qs = Position.objects.using(db).select_related("account").all()
    for pos in pos_qs.iterator(chunk_size=2000):
        account = getattr(pos, "account", None)
        if account is None:
            continue

        broker = (getattr(account, "broker", "") or "").upper()
        key = _account_key(account)

        if broker == "PAPER":
            paper_positions.append(
                PaperPosition(
                    user_id=getattr(account, "user_id", None),
                    account_key=key,
                    symbol=getattr(pos, "symbol", "") or "",
                    description=getattr(pos, "description", "") or "",
                    asset_type=getattr(pos, "asset_type", "EQ") or "EQ",
                    quantity=getattr(pos, "quantity", 0) or 0,
                    avg_price=getattr(pos, "avg_price", 0) or 0,
                    mark_price=getattr(pos, "mark_price", 0) or 0,
                    realized_pl_day=getattr(pos, "realized_pl_day", 0) or 0,
                    realized_pl_total=getattr(pos, "realized_pl_open", 0) or 0,
                    multiplier=getattr(pos, "multiplier", 1) or 1,
                    currency=getattr(pos, "currency", "USD") or "USD",
                )
            )

        elif broker == "SCHWAB":
            live_positions.append(
                LivePosition(
                    user_id=getattr(account, "user_id", None),
                    broker="SCHWAB",
                    broker_account_id=key,
                    symbol=getattr(pos, "symbol", "") or "",
                    description=getattr(pos, "description", "") or "",
                    asset_type=getattr(pos, "asset_type", "EQ") or "EQ",
                    quantity=getattr(pos, "quantity", 0) or 0,
                    avg_price=getattr(pos, "avg_price", 0) or 0,
                    mark_price=getattr(pos, "mark_price", 0) or 0,
                    broker_pl_day=getattr(pos, "realized_pl_day", 0) or 0,
                    broker_pl_ytd=getattr(pos, "realized_pl_open", 0) or 0,
                    multiplier=getattr(pos, "multiplier", 1) or 1,
                    currency=getattr(pos, "currency", "USD") or "USD",
                    broker_payload=None,
                )
            )

    if paper_positions:
        PaperPosition.objects.using(db).bulk_create(paper_positions, ignore_conflicts=True, batch_size=2000)

    if live_positions:
        LivePosition.objects.using(db).bulk_create(live_positions, ignore_conflicts=True, batch_size=2000)

    # --- Orders --------------------------------------------------------------
    paper_orders = []
    live_orders = []

    order_qs = Order.objects.using(db).select_related("account").all()
    for order in order_qs.iterator(chunk_size=2000):
        account = getattr(order, "account", None)
        if account is None:
            continue

        broker = (getattr(account, "broker", "") or "").upper()
        key = _account_key(account)

        if broker == "PAPER":
            paper_orders.append(
                PaperOrder(
                    user_id=getattr(account, "user_id", None),
                    account_key=key,
                    client_order_id=getattr(order, "broker_order_id", "") or "",
                    symbol=getattr(order, "symbol", "") or "",
                    asset_type=getattr(order, "asset_type", "EQ") or "EQ",
                    side=getattr(order, "side", "") or "",
                    quantity=getattr(order, "quantity", 0) or 0,
                    order_type=getattr(order, "order_type", "LMT") or "LMT",
                    limit_price=getattr(order, "limit_price", None),
                    stop_price=getattr(order, "stop_price", None),
                    status=getattr(order, "status", "WORKING") or "WORKING",
                    time_placed=getattr(order, "time_placed", None),
                )
            )

        elif broker == "SCHWAB":
            live_orders.append(
                LiveOrder(
                    user_id=getattr(account, "user_id", None),
                    broker="SCHWAB",
                    broker_account_id=key,
                    broker_order_id=getattr(order, "broker_order_id", "") or "",
                    status=getattr(order, "status", "WORKING") or "WORKING",
                    symbol=getattr(order, "symbol", "") or "",
                    asset_type=getattr(order, "asset_type", "EQ") or "EQ",
                    side=getattr(order, "side", "") or "",
                    quantity=getattr(order, "quantity", 0) or 0,
                    order_type=getattr(order, "order_type", "LMT") or "LMT",
                    limit_price=getattr(order, "limit_price", None),
                    stop_price=getattr(order, "stop_price", None),
                    broker_payload=None,
                    time_placed=getattr(order, "time_placed", None),
                )
            )

    # Note: PaperOrder/LiveOrder have auto_now fields (time_last_update) so we
    # don't attempt to backfill them precisely in a one-time migration.
    if paper_orders:
        PaperOrder.objects.using(db).bulk_create(paper_orders, ignore_conflicts=True, batch_size=2000)

    if live_orders:
        LiveOrder.objects.using(db).bulk_create(live_orders, ignore_conflicts=True, batch_size=2000)


def backwards(_apps, _schema_editor):
    # One-way migration; do not attempt to delete user history.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ActAndPos", "0013_liveorder_paperorder_livebalance_liveexecution_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
