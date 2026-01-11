from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from ..models import LiveOrder


class LiveOrderRouterError(Exception):
	pass


class UnsupportedBroker(LiveOrderRouterError):
	pass


@dataclass(frozen=True)
class LiveSubmitOrderParams:
	user_id: int
	broker: str
	broker_account_id: str
	symbol: str
	asset_type: str
	side: str
	quantity: Decimal
	order_type: str = "MKT"
	limit_price: Decimal | None = None
	stop_price: Decimal | None = None


def submit_order(params: LiveSubmitOrderParams) -> LiveOrder:
	"""Record a live order submission.

	Hard rule: we do not simulate fills for LIVE. This function only creates a
	LiveOrder row in SUBMITTED state. Broker adapters can later be plugged in
	to actually send the order and update broker_order_id/status.
	"""

	broker = (params.broker or "").upper()
	if broker not in {"SCHWAB"}:
		raise UnsupportedBroker(f"Unsupported broker: {broker}")

	symbol = (params.symbol or "").upper().strip()
	if not symbol:
		raise LiveOrderRouterError("symbol is required")

	side = (params.side or "").upper().strip()
	if side not in {"BUY", "SELL"}:
		raise LiveOrderRouterError("side must be BUY or SELL")

	order = LiveOrder.objects.create(
		user_id=params.user_id,
		broker=broker,
		broker_account_id=str(params.broker_account_id),
		broker_order_id="",
		status="SUBMITTED",
		symbol=symbol,
		asset_type=(params.asset_type or "EQ").upper(),
		side=side,
		quantity=params.quantity,
		order_type=(params.order_type or "MKT").upper(),
		limit_price=params.limit_price,
		stop_price=params.stop_price,
		broker_payload={
			"submitted_at": timezone.now().isoformat(),
			"broker": broker,
			"broker_account_id": str(params.broker_account_id),
			"symbol": symbol,
			"side": side,
			"quantity": str(params.quantity),
			"order_type": (params.order_type or "MKT").upper(),
		},
		time_placed=timezone.now(),
	)

	return order


def cancel_order(*, user_id: int, live_order_id: int) -> LiveOrder:
	"""Mark a live order as cancel requested.

	Broker cancel is not wired yet.
	"""

	order = LiveOrder.objects.get(pk=live_order_id, user_id=user_id)
	order.status = "CANCEL_REQUESTED"
	order.save(update_fields=["status", "time_last_update"])
	return order


def replace_order(*, user_id: int, live_order_id: int, **_changes) -> LiveOrder:
	"""Mark a live order as replace requested.

	Broker replace is not wired yet.
	"""

	order = LiveOrder.objects.get(pk=live_order_id, user_id=user_id)
	order.status = "REPLACE_REQUESTED"
	order.save(update_fields=["status", "time_last_update"])
	return order
