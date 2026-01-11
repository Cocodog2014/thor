from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.live.models import LiveOrder
from ActAndPos.live.services.order_router import LiveSubmitOrderParams, cancel_order as cancel_live_order, submit_order as submit_live_order
from ActAndPos.paper.engine import InvalidPaperOrder, PaperOrderParams, submit_order as submit_paper_order
from ActAndPos.paper.models import PaperOrder
from ActAndPos.shared.accounts import get_active_account, resolve_account_for_user, serialize_active_account


def _serialize_position(pk, symbol, description, asset_type, quantity, avg_price, mark_price, multiplier, realized_pl_open, realized_pl_day, currency):
    """Serialize a position object to a dict."""
    return {
        "id": pk,
        "symbol": symbol,
        "description": description,
        "asset_type": asset_type,
        "quantity": quantity,
        "avg_price": avg_price,
        "mark_price": mark_price,
        "multiplier": multiplier,
        "realized_pl_open": realized_pl_open,
        "realized_pl_day": realized_pl_day,
        "currency": currency,
    }



def _parse_decimal(value, field_name: str, allow_null: bool = False):
    if value in (None, "", "null"):
        if allow_null:
            return None
        raise ValueError(f"{field_name} is required.")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid {field_name}.")


def _to_decimal(val):
    if val is None or val == "":
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _field_error_response(field: str, exc: Exception) -> Response:
    """Return a consistent JSON error payload for form validation issues."""

    return Response({"field": field, "detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _normalize_symbol(raw):
    """
    Normalize and validate the instrument symbol.

    - Uppercase & strip whitespace
    - Require at least 1 character
    - Uppercase & strip whitespace
    - Allow broker symbols like /ES and $DXY
    """

    symbol = (raw or "").upper().strip()
    if not symbol:
        raise ValueError("symbol is required.")
    return symbol


def _serialize_order_like(
    *,
    pk: int,
    symbol: str,
    asset_type: str,
    side: str,
    quantity,
    order_type: str,
    limit_price,
    stop_price,
    status: str,
    time_placed,
    time_last_update,
    time_filled=None,
    time_canceled=None,
) -> dict:
    def _as_str(v):
        return "" if v is None else str(v)

    return {
        "id": pk,
        "symbol": str(symbol or "").upper(),
        "asset_type": str(asset_type or "EQ").upper(),
        "side": str(side or "BUY").upper(),
        "quantity": _as_str(quantity),
        "order_type": str(order_type or "MKT").upper(),
        "limit_price": _as_str(limit_price) if limit_price is not None else None,
        "stop_price": _as_str(stop_price) if stop_price is not None else None,
        "status": str(status or "WORKING").upper(),
        "time_placed": time_placed.isoformat() if time_placed else timezone.now().isoformat(),
        "time_last_update": time_last_update.isoformat() if time_last_update else timezone.now().isoformat(),
        "time_filled": time_filled.isoformat() if time_filled else None,
        "time_canceled": time_canceled.isoformat() if time_canceled else None,
    }


@api_view(["POST"])
def order_create_active_view(request):
    """
    POST /trades/orders/active

    Create an order for the *active* account (from session or ?account_id=),
    route it through the unified order_engine, and return the updated snapshot.
    """

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data

    return _order_create_for_account(request=request, account=account, data=data)


def _order_create_for_account(*, request, account, data) -> Response:

    # --- symbol / core fields ---
    try:
        symbol = _normalize_symbol(data.get("symbol"))
    except ValueError as exc:
        return _field_error_response("symbol", exc)

    asset_type = (data.get("asset_type") or "EQ").upper()
    side = (data.get("side") or "").upper()
    order_type = (data.get("order_type") or "MKT").upper()

    try:
        quantity = _parse_decimal(data.get("quantity"), "quantity")
    except ValueError as exc:
        return _field_error_response("quantity", exc)

    try:
        limit_price = _parse_decimal(
            data.get("limit_price"), "limit_price", allow_null=True
        )
    except ValueError as exc:
        return _field_error_response("limit_price", exc)

    try:
        stop_price = _parse_decimal(
            data.get("stop_price"), "stop_price", allow_null=True
        )
    except ValueError as exc:
        return _field_error_response("stop_price", exc)

    if str(account.broker).upper() == "PAPER":
        try:
            order, _fill, position, _balance = submit_paper_order(
                PaperOrderParams(
                    user_id=request.user.id,
                    account_key=str(account.broker_account_id),
                    symbol=symbol,
                    asset_type=asset_type,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    limit_price=limit_price,
                    stop_price=stop_price,
                )
            )
        except InvalidPaperOrder as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        account_summary = serialize_active_account(request=request, account=account)
        order_payload = _serialize_order_like(
            pk=order.pk,
            symbol=order.symbol,
            asset_type=order.asset_type,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            status=order.status,
            time_placed=order.time_placed,
            time_last_update=order.time_last_update,
        )

        position_payload = _serialize_position(
            pk=position.pk,
            symbol=str(position.symbol or "").upper(),
            description=position.description or "",
            asset_type=str(position.asset_type or "EQ").upper(),
            quantity=position.quantity,
            avg_price=position.avg_price,
            mark_price=position.mark_price,
            multiplier=position.multiplier,
            realized_pl_open=position.realized_pl_total,
            realized_pl_day=position.realized_pl_day,
            currency=position.currency or "USD",
        )

        return Response(
            {"account": account_summary, "order": order_payload, "position": position_payload},
            status=status.HTTP_201_CREATED,
        )

    # LIVE
    try:
        order = submit_live_order(
            LiveSubmitOrderParams(
                user_id=request.user.id,
                broker=str(account.broker or "SCHWAB"),
                broker_account_id=str(account.broker_account_id),
                symbol=symbol,
                asset_type=asset_type,
                side=side,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
            )
        )
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    account_summary = serialize_active_account(request=request, account=account)
    order_payload = _serialize_order_like(
        pk=order.pk,
        symbol=order.symbol,
        asset_type=order.asset_type,
        side=order.side,
        quantity=order.quantity,
        order_type=order.order_type,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        status=order.status,
        time_placed=order.time_placed,
        time_last_update=order.time_last_update,
    )
    return Response(
        {"account": account_summary, "order": order_payload, "position": None},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def order_create_view(request):
    """
    POST /trades/orders

    Create an order for a specific account_id, immediately fill it via
    the order_engine, and return the updated snapshot.
    """

    data = request.data

    account_id = data.get("account_id")
    if not account_id:
        return Response({"detail": "account_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        account = resolve_account_for_user(user=request.user, account_id=str(account_id))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    # --- core fields ---
    try:
        symbol = _normalize_symbol(data.get("symbol"))
    except ValueError as exc:
        return _field_error_response("symbol", exc)

    side = (data.get("side") or "").upper()
    order_type = (data.get("order_type") or "MKT").upper()
    asset_type = (data.get("asset_type") or "EQ").upper()
    quantity_raw = data.get("quantity")

    if not side:
        return _field_error_response("side", ValueError("side is required."))
    if quantity_raw in (None, ""):
        return _field_error_response("quantity", ValueError("quantity is required."))

    try:
        quantity = Decimal(str(quantity_raw))
    except Exception:
        return _field_error_response("quantity", ValueError("quantity must be a number."))

    try:
        limit_price = _to_decimal(data.get("limit_price"))
    except ValueError as exc:
        return _field_error_response("limit_price", exc)

    try:
        stop_price = _to_decimal(data.get("stop_price"))
    except ValueError as exc:
        return _field_error_response("stop_price", exc)

    return _order_create_for_account(request=request, account=account, data=data)


@api_view(["POST"])
def order_cancel_view(request, pk: int):
    """
    POST /trades/orders/<pk>/cancel

    Cancel a WORKING order. Right now it only allows PAPER accounts,
    but the name is generic so we can extend it to other brokers later.
    """

    # PAPER first
    order = PaperOrder.objects.filter(pk=pk, user=request.user).first()
    if order is not None:
        if str(order.status or "").upper() != "WORKING":
            return Response(
                {"detail": f"Only WORKING orders can be canceled (current status: {order.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        order.status = "CANCELED"
        order.time_last_update = now
        order.save(update_fields=["status", "time_last_update"])

        return Response(
            _serialize_order_like(
                pk=order.pk,
                symbol=order.symbol,
                asset_type=order.asset_type,
                side=order.side,
                quantity=order.quantity,
                order_type=order.order_type,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                status=order.status,
                time_placed=order.time_placed,
                time_last_update=order.time_last_update,
                time_canceled=now,
            ),
            status=status.HTTP_200_OK,
        )

    # LIVE fallback
    live_order = LiveOrder.objects.filter(pk=pk, user=request.user).first()
    if live_order is None:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        live_order = cancel_live_order(user_id=request.user.id, live_order_id=live_order.id)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        _serialize_order_like(
            pk=live_order.pk,
            symbol=live_order.symbol,
            asset_type=live_order.asset_type,
            side=live_order.side,
            quantity=live_order.quantity,
            order_type=live_order.order_type,
            limit_price=live_order.limit_price,
            stop_price=live_order.stop_price,
            status=live_order.status,
            time_placed=live_order.time_placed,
            time_last_update=live_order.time_last_update,
        ),
        status=status.HTTP_200_OK,
    )

