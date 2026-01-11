"""Sync Schwab balances/positions/orders into Live* models.

This is the LIVE-side Schwab integration.

- Balances/positions/orders are fetched from Schwab Trader API and mapped into
  ActAndPos.live.models (LiveBalance/LivePosition/LiveOrder).
- Marks/quotes remain sourced from LiveData (streamer) and consumed via
  ActAndPos.shared.marketdata.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from django.utils import timezone

from ActAndPos.live.models import LiveBalance, LiveOrder, LivePosition

from LiveData.schwab.client.tokens import ensure_valid_access_token
from LiveData.schwab.utils import get_schwab_connection

try:
	from LiveData.shared.redis_client import live_data_redis
except Exception:  # pragma: no cover
	live_data_redis = None  # type: ignore


logger = logging.getLogger(__name__)

ACCOUNT_NUMBERS_CACHE_KEY = "live_data:schwab:account_numbers"
ACCOUNT_NUMBERS_CACHE_TTL = 60  # seconds


@dataclass(frozen=True)
class SchwabSyncResult:
	account_hash: str
	balances_upserted: bool
	positions_upserted: int
	positions_deleted: int
	orders_upserted: int


def _dec(value: Any, default: Decimal = Decimal("0")) -> Decimal:
	try:
		return Decimal(str(value if value is not None else default))
	except Exception:
		return default


def _first_numeric(row: Dict[str, Any], keys: Iterable[str]) -> Decimal:
	for key in keys:
		if key in row:
			val = row.get(key)
			d = _dec(val, default=Decimal("0"))
			if d != Decimal("0"):
				return d
	# Treat explicit 0 as a valid value if present on any key.
	for key in keys:
		if key in row:
			return _dec(row.get(key), default=Decimal("0"))
	return Decimal("0")


def _looks_like_hash(value: str) -> bool:
	return bool(value and re.fullmatch(r"[A-Fa-f0-9]{32,128}", str(value).strip()))


def _looks_like_account_number(value: str) -> bool:
	value = str(value or "").strip()
	return bool(value.isdigit() and 6 <= len(value) <= 12)


def _redis_client():
	client = getattr(live_data_redis, "client", None) if live_data_redis is not None else None
	return client


def _fetch_account_numbers_map(user) -> Dict[str, str]:
	"""Return mapping of accountNumber -> hashValue from /accounts/accountNumbers.

	Uses Redis caching when available.
	"""

	client = _redis_client()
	if client is not None:
		try:
			cached = client.get(ACCOUNT_NUMBERS_CACHE_KEY)
			if cached:
				import json

				parsed = json.loads(cached)
				if isinstance(parsed, dict):
					return {str(k): str(v) for k, v in parsed.items()}
		except Exception:
			pass

	api = _SchwabTradingClient(user)
	data = api.request_json("GET", "/accounts/accountNumbers")

	mapping: Dict[str, str] = {}
	if isinstance(data, list):
		for row in data:
			if not isinstance(row, dict):
				continue
			number = str(row.get("accountNumber") or "").strip()
			hash_val = str(row.get("hashValue") or "").strip()
			if number and hash_val:
				mapping[number] = hash_val

	if client is not None:
		try:
			import json

			client.set(ACCOUNT_NUMBERS_CACHE_KEY, json.dumps(mapping), ex=ACCOUNT_NUMBERS_CACHE_TTL)
		except Exception:
			pass

	return mapping


def resolve_account_hash(user, broker_account_id: str) -> str:
	"""Accept accountNumber or hashValue and return hashValue."""

	account_id = str(broker_account_id or "").strip()
	if not account_id:
		raise ValueError("broker_account_id is required")

	if _looks_like_hash(account_id):
		return account_id

	if _looks_like_account_number(account_id):
		mapping = _fetch_account_numbers_map(user)
		resolved = mapping.get(account_id)
		if resolved:
			return resolved

	raise ValueError(f"Unable to resolve Schwab account hash for account_id={account_id}")


class _SchwabTradingClient:
	BASE_URL = "https://api.schwabapi.com/trader/v1"

	def __init__(self, user):
		self.user = user
		conn = get_schwab_connection(user)
		if not conn:
			raise RuntimeError("User does not have a Schwab connection")
		conn = ensure_valid_access_token(conn)
		self.conn = conn

	def _headers(self) -> Dict[str, str]:
		return {
			"Authorization": f"Bearer {self.conn.access_token}",
			"Accept": "application/json",
		}

	def request_json(self, method: str, path: str, *, retry_on_unauthorized: bool = True, **kwargs):
		path_clean = (path or "").lstrip("/")
		base = self.BASE_URL.rstrip("/")
		if base.endswith("/trader/v1") and path_clean.startswith("trader/v1/"):
			path_clean = path_clean[len("trader/v1/") :]
		url = f"{base}/{path_clean}"
		req_kwargs = dict(kwargs)
		req_kwargs.setdefault("timeout", 12)

		# proactive refresh
		self.conn = ensure_valid_access_token(self.conn)

		resp = requests.request(method, url, headers=self._headers(), **req_kwargs)
		if resp.status_code == 401 and retry_on_unauthorized:
			logger.warning("Schwab API 401 for %s %s — retrying after refresh", method, path)
			self.conn = ensure_valid_access_token(self.conn, force_refresh=True)
			resp = requests.request(method, url, headers=self._headers(), **req_kwargs)

		resp.raise_for_status()
		return resp.json()


def _normalize_balances_payload(account_hash: str, sec: Dict[str, Any]) -> Dict[str, Any]:
	bal = sec.get("currentBalances") or sec.get("initialBalances") or sec.get("balances") or {}
	if not isinstance(bal, dict):
		bal = {}

	net_liq = bal.get("liquidationValue") or bal.get("netLiquidation") or 0
	stock_bp = bal.get("stockBuyingPower") or bal.get("buyingPower") or bal.get("cashBuyingPower") or 0
	option_bp = bal.get("optionBuyingPower") or 0
	daytrade_bp = bal.get("dayTradingBuyingPower") or 0
	cash = bal.get("cashBalance") or bal.get("cashAvailableForTrading") or bal.get("availableFunds") or 0
	equity = bal.get("equity") or net_liq or 0

	return {
		"account_hash": account_hash,
		"account_number": sec.get("accountNumber"),
		"net_liq": float(net_liq or 0),
		"cash": float(cash or 0),
		"equity": float(equity or 0),
		"stock_buying_power": float(stock_bp or 0),
		"option_buying_power": float(option_bp or 0),
		"day_trading_buying_power": float(daytrade_bp or 0),
	}


def _normalize_positions(raw_positions: Iterable[Any]) -> List[Dict[str, Any]]:
	out: List[Dict[str, Any]] = []
	for pos in raw_positions or []:
		if not isinstance(pos, dict):
			continue
		instrument = pos.get("instrument") or {}
		if not isinstance(instrument, dict):
			instrument = {}

		symbol = instrument.get("symbol") or instrument.get("underlyingSymbol")
		symbol = str(symbol or "").strip().upper()
		if not symbol:
			continue

		raw_asset = str(instrument.get("assetType") or "EQ").upper()
		asset_type = "EQ" if raw_asset in {"EQ", "EQUITY"} else raw_asset

		long_qty = _dec(pos.get("longQuantity"), Decimal("0"))
		short_qty = _dec(pos.get("shortQuantity"), Decimal("0"))
		quantity = long_qty - short_qty

		avg_price = _dec(pos.get("averagePrice"), Decimal("0"))
		market_value = _dec(pos.get("marketValue"), Decimal("0"))

		# Schwab position payloads commonly include current-day P/L and may include YTD P/L.
		# We accept multiple possible key names defensively.
		pl_day = _first_numeric(
			pos,
			(
				"currentDayProfitLoss",
				"currentDayProfitLossValue",
				"dayProfitLoss",
				"dayPnl",
				"profitLossDay",
			),
		)
		pl_ytd = _first_numeric(
			pos,
			(
				"yearToDateProfitLoss",
				"ytdProfitLoss",
				"profitLossYTD",
				"ytdPnl",
			),
		)

		multiplier = _dec(
			instrument.get("multiplier")
			or pos.get("multiplier")
			or pos.get("contractMultiplier")
			or Decimal("1"),
			Decimal("1"),
		)
		mark_price = Decimal("0")
		if quantity:
			try:
				mark_price = market_value / quantity
			except Exception:
				mark_price = Decimal("0")

		out.append(
			{
				"symbol": symbol,
				"asset_type": asset_type,
				"description": str(instrument.get("description") or ""),
				"quantity": float(quantity),
				"avg_price": float(avg_price),
				"mark_price": float(mark_price),
				"broker_pl_day": float(pl_day),
				"broker_pl_ytd": float(pl_ytd),
				"multiplier": float(multiplier),
				"market_value": float(market_value),
				"currency": str(pos.get("settlementCurrency") or "USD"),
				"raw": pos,
			}
		)
	return out


def _normalize_orders(raw_orders: Any) -> List[Dict[str, Any]]:
	if not isinstance(raw_orders, list):
		return []
	out: List[Dict[str, Any]] = []
	for row in raw_orders:
		if not isinstance(row, dict):
			continue

		broker_order_id = str(row.get("orderId") or row.get("order_id") or "").strip()
		status = str(row.get("status") or "WORKING").upper()
		order_type = str(row.get("orderType") or row.get("order_type") or "MKT").upper()

		entered = row.get("enteredTime") or row.get("timePlaced")
		try:
			# enteredTime is usually ISO; leave parsing to Django if already dt.
			if isinstance(entered, str) and entered:
				time_placed = timezone.datetime.fromisoformat(entered.replace("Z", "+00:00"))
				if timezone.is_naive(time_placed):
					time_placed = timezone.make_aware(time_placed, timezone=timezone.utc)
			elif isinstance(entered, timezone.datetime):
				time_placed = entered
			else:
				time_placed = timezone.now()
		except Exception:
			time_placed = timezone.now()

		legs = row.get("orderLegCollection") or []
		leg0 = legs[0] if isinstance(legs, list) and legs else {}
		if not isinstance(leg0, dict):
			leg0 = {}
		instr = leg0.get("instrument") or {}
		if not isinstance(instr, dict):
			instr = {}

		symbol = str(instr.get("symbol") or instr.get("underlyingSymbol") or "").strip().upper()
		if not symbol:
			# skip non-instrument orders for now (multi-leg/etc)
			continue

		side = str(leg0.get("instruction") or row.get("orderLegInstruction") or "").upper()
		side = side if side in {"BUY", "SELL"} else "BUY"

		qty = _dec(leg0.get("quantity") or row.get("quantity"), Decimal("0"))

		raw_asset = str(instr.get("assetType") or "EQ").upper()
		asset_type = "EQ" if raw_asset in {"EQ", "EQUITY"} else raw_asset

		limit_price = row.get("price") or row.get("limitPrice") or row.get("limit_price")
		stop_price = row.get("stopPrice") or row.get("stop_price")

		out.append(
			{
				"broker_order_id": broker_order_id,
				"status": status,
				"symbol": symbol,
				"asset_type": asset_type,
				"side": side,
				"quantity": qty,
				"order_type": order_type,
				"limit_price": _dec(limit_price) if limit_price is not None else None,
				"stop_price": _dec(stop_price) if stop_price is not None else None,
				"time_placed": time_placed,
				"raw": row,
			}
		)
	return out


def sync_schwab_account(
	*,
	user,
	broker_account_id: str,
	include_orders: bool = True,
	orders_days: int = 7,
	publish_ws: bool = True,
) -> SchwabSyncResult:
	"""Fetch Schwab data and upsert Live* models for a single account."""

	account_hash = resolve_account_hash(user, broker_account_id)
	api = _SchwabTradingClient(user)

	# --- balances ----------------------------------------------------------
	details = api.request_json("GET", f"/accounts/{account_hash}")
	sec = (details.get("securitiesAccount") or {}) if isinstance(details, dict) else {}
	balances_payload = _normalize_balances_payload(account_hash, sec if isinstance(sec, dict) else {})

	LiveBalance.objects.update_or_create(
		user=user,
		broker="SCHWAB",
		broker_account_id=account_hash,
		defaults={
			"currency": "USD",
			"net_liq": _dec(balances_payload.get("net_liq")),
			"cash": _dec(balances_payload.get("cash")),
			"equity": _dec(balances_payload.get("equity"), _dec(balances_payload.get("net_liq"))),
			"stock_buying_power": _dec(balances_payload.get("stock_buying_power")),
			"option_buying_power": _dec(balances_payload.get("option_buying_power")),
			"day_trading_buying_power": _dec(balances_payload.get("day_trading_buying_power")),
			"broker_payload": details,
		},
	)

	# Optional: keep Redis snapshot current for other consumers.
	if live_data_redis is not None:
		snapshot = {
			"account_id": account_hash,
			"account_hash": account_hash,
			"updated_at": timezone.now().isoformat(),
			**balances_payload,
		}
		try:
			live_data_redis.set_json(f"live_data:balances:{account_hash}", snapshot)
		except Exception:
			pass
		try:
			live_data_redis.publish_balance(account_hash, snapshot, broadcast_ws=publish_ws)
		except Exception:
			logger.exception("Failed to publish Schwab balances for %s", account_hash)

	# --- positions ---------------------------------------------------------
	details_pos = api.request_json("GET", f"/accounts/{account_hash}", params={"fields": "positions"})
	sec_pos = (details_pos.get("securitiesAccount") or {}) if isinstance(details_pos, dict) else {}
	raw_positions = (sec_pos.get("positions") or []) if isinstance(sec_pos, dict) else []
	normalized_positions = _normalize_positions(raw_positions)

	seen_keys: set[Tuple[str, str]] = set()
	for row in normalized_positions:
		symbol = str(row.get("symbol") or "").upper()
		asset_type = str(row.get("asset_type") or "EQ").upper()
		if not symbol:
			continue
		seen_keys.add((symbol, asset_type))
		LivePosition.objects.update_or_create(
			user=user,
			broker="SCHWAB",
			broker_account_id=account_hash,
			symbol=symbol,
			asset_type=asset_type,
			defaults={
				"description": str(row.get("description") or ""),
				"quantity": _dec(row.get("quantity")),
				"avg_price": _dec(row.get("avg_price")),
				"mark_price": _dec(row.get("mark_price")),
				"broker_pl_day": _dec(row.get("broker_pl_day")),
				"broker_pl_ytd": _dec(row.get("broker_pl_ytd")),
				"multiplier": _dec(row.get("multiplier"), Decimal("1")),
				"currency": str(row.get("currency") or "USD"),
				"broker_payload": row.get("raw") if isinstance(row.get("raw"), dict) else row,
			},
		)

	# Delete stale positions (symbols no longer held)
	deleted = 0
	qs = LivePosition.objects.filter(user=user, broker="SCHWAB", broker_account_id=account_hash)
	for pos in qs:
		key = (str(pos.symbol).upper(), str(pos.asset_type).upper())
		if key not in seen_keys:
			pos.delete()
			deleted += 1

	if live_data_redis is not None:
		snapshot = {
			"account_id": account_hash,
			"account_hash": account_hash,
			"updated_at": timezone.now().isoformat(),
			"positions": [
				{
					"symbol": p["symbol"],
					"asset_type": p["asset_type"],
					"quantity": p["quantity"],
					"avg_price": p["avg_price"],
					"mark_price": p["mark_price"],
						"broker_pl_day": p.get("broker_pl_day", 0),
						"broker_pl_ytd": p.get("broker_pl_ytd", 0),
						"multiplier": p.get("multiplier", 1),
					"description": p.get("description") or "",
					"currency": p.get("currency") or "USD",
				}
				for p in normalized_positions
			],
		}
		try:
			live_data_redis.set_json(f"live_data:positions:{account_hash}", snapshot)
		except Exception:
			pass
		try:
			live_data_redis.publish_positions(account_hash, snapshot, broadcast_ws=publish_ws)
		except Exception:
			logger.exception("Failed to publish Schwab positions for %s", account_hash)

	# --- orders ------------------------------------------------------------
	orders_upserted = 0
	if include_orders:
		now = timezone.now()
		from_dt = now - timedelta(days=max(1, int(orders_days)))
		params = {
			"fromEnteredTime": from_dt.isoformat(),
			"toEnteredTime": now.isoformat(),
		}
		raw_orders = api.request_json("GET", f"/accounts/{account_hash}/orders", params=params)
		normalized_orders = _normalize_orders(raw_orders)
		for row in normalized_orders:
			broker_order_id = str(row.get("broker_order_id") or "").strip()
			if not broker_order_id:
				continue
			LiveOrder.objects.update_or_create(
				user=user,
				broker="SCHWAB",
				broker_account_id=account_hash,
				broker_order_id=broker_order_id,
				defaults={
					"status": str(row.get("status") or "WORKING"),
					"symbol": str(row.get("symbol") or "").upper(),
					"asset_type": str(row.get("asset_type") or "EQ").upper(),
					"side": str(row.get("side") or "BUY"),
					"quantity": _dec(row.get("quantity")),
					"order_type": str(row.get("order_type") or "MKT"),
					"limit_price": row.get("limit_price"),
					"stop_price": row.get("stop_price"),
					"time_placed": row.get("time_placed") or timezone.now(),
					"broker_payload": row.get("raw") if isinstance(row.get("raw"), dict) else row,
				},
			)
			orders_upserted += 1

			if live_data_redis is not None:
				try:
					live_data_redis.publish_order(
						account_hash,
						{
							"broker": "SCHWAB",
							"broker_order_id": broker_order_id,
							"status": str(row.get("status") or "WORKING"),
							"symbol": str(row.get("symbol") or "").upper(),
							"side": str(row.get("side") or "BUY"),
							"quantity": str(row.get("quantity") or "0"),
							"order_type": str(row.get("order_type") or "MKT"),
							"limit_price": str(row.get("limit_price")) if row.get("limit_price") is not None else None,
							"stop_price": str(row.get("stop_price")) if row.get("stop_price") is not None else None,
							"updated_at": timezone.now().isoformat(),
						},
						broadcast_ws=publish_ws,
					)
				except Exception:
					logger.exception("Failed to publish Schwab order %s for %s", broker_order_id, account_hash)

	return SchwabSyncResult(
		account_hash=account_hash,
		balances_upserted=True,
		positions_upserted=len(normalized_positions),
		positions_deleted=deleted,
		orders_upserted=orders_upserted,
	)

