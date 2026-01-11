from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from ActAndPos.shared.marketdata import get_mark

from .models import PaperBalance, PaperFill, PaperOrder, PaperPosition

try:
	from LiveData.shared.redis_client import live_data_redis
except Exception:  # pragma: no cover
	live_data_redis = None  # type: ignore


DEFAULT_PAPER_CASH = Decimal("100000.00")


class PaperEngineError(Exception):
	pass


class InvalidPaperAccount(PaperEngineError):
	pass


class InsufficientBuyingPower(PaperEngineError):
	pass


class InvalidPaperOrder(PaperEngineError):
	pass


@dataclass(frozen=True)
class PaperOrderParams:
	user_id: int
	account_key: str
	symbol: str
	asset_type: str
	side: str
	quantity: Decimal
	order_type: str = "MKT"
	limit_price: Decimal | None = None
	stop_price: Decimal | None = None
	client_order_id: str = ""
	commission: Decimal = Decimal("0")
	fees: Decimal = Decimal("0")


def _require_paper_account_key(account_key: str) -> str:
	key = str(account_key or "").strip()
	if not key:
		raise InvalidPaperAccount("account_key is required")
	# Hard rule: paper engine never takes live accounts.
	# We use a strong convention: paper accounts are always prefixed.
	if not key.upper().startswith("PAPER-"):
		raise InvalidPaperAccount("paper engine only accepts PAPER-* account keys")
	return key


def _to_dec(value, default: Decimal = Decimal("0")) -> Decimal:
	if value is None:
		return default
	if isinstance(value, Decimal):
		return value
	try:
		return Decimal(str(value))
	except Exception:
		return default


def ensure_balance(*, user_id: int, account_key: str) -> PaperBalance:
	account_key = _require_paper_account_key(account_key)
	bal, _ = PaperBalance.objects.get_or_create(
		user_id=user_id,
		account_key=account_key,
		defaults={
			"currency": "USD",
			"cash": DEFAULT_PAPER_CASH,
			"equity": DEFAULT_PAPER_CASH,
			"net_liq": DEFAULT_PAPER_CASH,
			"buying_power": DEFAULT_PAPER_CASH * 4,
			"day_trade_bp": DEFAULT_PAPER_CASH * 4,
		},
	)
	return bal


def _recompute_balance(*, user_id: int, account_key: str) -> PaperBalance:
	bal = ensure_balance(user_id=user_id, account_key=account_key)
	positions = PaperPosition.objects.filter(user_id=user_id, account_key=account_key)
	total_mv = sum((p.market_value for p in positions), Decimal("0"))
	bal.net_liq = (bal.cash or Decimal("0")) + total_mv
	bal.equity = bal.net_liq
	bal.buying_power = bal.net_liq * 4
	bal.day_trade_bp = bal.net_liq * 4
	bal.save(update_fields=["net_liq", "equity", "buying_power", "day_trade_bp", "updated_at"])
	return bal


def _fill_price(params: PaperOrderParams) -> Decimal:
	if params.order_type in ("LMT", "STP_LMT") and params.limit_price is not None:
		return params.limit_price
	mark = get_mark(params.symbol)
	return mark if mark is not None else Decimal("100")


def _publish_realtime(*, user_id: int, account_key: str) -> None:
	if live_data_redis is None:
		return

	bal = PaperBalance.objects.filter(user_id=user_id, account_key=account_key).first()
	if bal is None:
		return

	positions = PaperPosition.objects.filter(user_id=user_id, account_key=account_key).order_by("symbol")
	positions_payload = [
		{
			"symbol": p.symbol,
			"description": p.description or "",
			"asset_type": p.asset_type,
			"quantity": float(p.quantity or 0),
			"avg_price": float(p.avg_price or 0),
			"mark_price": float(p.mark_price or 0),
			"market_value": float(p.market_value or 0),
			"realized_pl_day": float(p.realized_pl_day or 0),
			"realized_pl_open": float(p.realized_pl_total or 0),
			"multiplier": float(p.multiplier or 1),
			"currency": p.currency or "USD",
		}
		for p in positions
	]

	now = timezone.now().isoformat()
	balances_payload = {
		"broker": "PAPER",
		"account_key": account_key,
		"net_liq": float(bal.net_liq or 0),
		"cash": float(bal.cash or 0),
		"equity": float(bal.equity or 0),
		"stock_buying_power": float(bal.buying_power or 0),
		"option_buying_power": 0.0,
		"day_trading_buying_power": float(bal.day_trade_bp or 0),
		"updated_at": now,
	}

	snapshot_positions = {
		"broker": "PAPER",
		"account_key": account_key,
		"positions": positions_payload,
		"updated_at": now,
	}

	# Mirror the same key shape used elsewhere in the app.
	try:
		live_data_redis.set_json(f"live_data:balances:{account_key}", balances_payload)
		live_data_redis.set_json(f"live_data:positions:{account_key}", snapshot_positions)
	except Exception:
		pass

	try:
		live_data_redis.publish_balance(account_key, balances_payload, broadcast_ws=True)
		live_data_redis.publish_positions(account_key, snapshot_positions, broadcast_ws=True)
	except Exception:
		# Realtime failure should never block paper execution.
		return


@transaction.atomic
def submit_order(params: PaperOrderParams) -> tuple[PaperOrder, PaperFill, PaperPosition, PaperBalance]:
	account_key = _require_paper_account_key(params.account_key)
	symbol = (params.symbol or "").upper().strip()
	if not symbol:
		raise InvalidPaperOrder("symbol is required")

	asset_type = (params.asset_type or "EQ").upper()
	side = (params.side or "").upper()
	if side not in {"BUY", "SELL"}:
		raise InvalidPaperOrder("side must be BUY or SELL")

	qty = _to_dec(params.quantity)
	if qty <= 0:
		raise InvalidPaperOrder("quantity must be positive")

	bal = ensure_balance(user_id=params.user_id, account_key=account_key)
	price = _fill_price(params)
	notional = price * qty

	if side == "BUY" and (bal.day_trade_bp or Decimal("0")) < notional:
		raise InsufficientBuyingPower("Insufficient buying power")

	order = PaperOrder.objects.create(
		user_id=params.user_id,
		account_key=account_key,
		client_order_id=params.client_order_id or "",
		symbol=symbol,
		asset_type=asset_type,
		side=side,
		quantity=qty,
		order_type=(params.order_type or "MKT").upper(),
		limit_price=params.limit_price,
		stop_price=params.stop_price,
		status="FILLED",
		time_placed=timezone.now(),
	)

	fill = PaperFill.objects.create(
		user_id=params.user_id,
		account_key=account_key,
		order=order,
		exec_id="",
		symbol=symbol,
		side=side,
		quantity=qty,
		price=price,
		commission=params.commission or Decimal("0"),
		fees=params.fees or Decimal("0"),
		exec_time=timezone.now(),
	)

	position, _ = PaperPosition.objects.select_for_update().get_or_create(
		user_id=params.user_id,
		account_key=account_key,
		symbol=symbol,
		asset_type=asset_type,
		defaults={
			"description": "",
			"quantity": Decimal("0"),
			"avg_price": price,
			"mark_price": price,
			"multiplier": Decimal("1"),
		},
	)

	commission = params.commission or Decimal("0")
	fees = params.fees or Decimal("0")
	mult = position.multiplier or Decimal("1")

	if side == "BUY":
		q_old = position.quantity or Decimal("0")
		q_new = q_old + qty
		if q_old == 0:
			avg_new = price
		else:
			avg_new = (q_old * (position.avg_price or Decimal("0")) + qty * price) / q_new
		position.quantity = q_new
		position.avg_price = avg_new
		position.mark_price = price
		position.save()

		bal.cash = (bal.cash or Decimal("0")) - (notional * mult + commission + fees)
		bal.save(update_fields=["cash", "updated_at"])

	else:
		q_old = position.quantity or Decimal("0")
		if qty > q_old:
			raise InvalidPaperOrder("Cannot sell more than current position")
		q_new = q_old - qty

		realized = (price - (position.avg_price or Decimal("0"))) * qty * mult
		position.realized_pl_day = (position.realized_pl_day or Decimal("0")) + realized
		position.realized_pl_total = (position.realized_pl_total or Decimal("0")) + realized
		position.quantity = q_new
		position.mark_price = price
		position.save()

		bal.cash = (bal.cash or Decimal("0")) + (notional * mult) - (commission + fees)
		bal.save(update_fields=["cash", "updated_at"])

	bal = _recompute_balance(user_id=params.user_id, account_key=account_key)

	# Broadcast snapshots + the newly created order.
	_publish_realtime(user_id=params.user_id, account_key=account_key)

	if live_data_redis is not None:
		order_payload = {
			"broker": "PAPER",
			"account_key": account_key,
			"order_id": str(order.id),
			"client_order_id": order.client_order_id,
			"symbol": order.symbol,
			"asset_type": order.asset_type,
			"side": order.side,
			"quantity": float(order.quantity or 0),
			"order_type": order.order_type,
			"limit_price": float(order.limit_price) if order.limit_price is not None else None,
			"stop_price": float(order.stop_price) if order.stop_price is not None else None,
			"status": order.status,
			"time_placed": order.time_placed.isoformat() if order.time_placed else None,
			"updated_at": timezone.now().isoformat(),
		}
		try:
			live_data_redis.set_json(f"live_data:orders:{account_key}", {"order": order_payload, "updated_at": order_payload["updated_at"]})
		except Exception:
			pass
		try:
			live_data_redis.publish_order(account_key, order_payload, broadcast_ws=True)
		except Exception:
			pass

	return order, fill, position, bal
