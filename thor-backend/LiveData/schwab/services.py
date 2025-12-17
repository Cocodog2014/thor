"""
Schwab Trading API client.
"""

import logging
import re
import requests
from typing import Dict, List, Optional
from decimal import Decimal
from json import dumps, loads

from LiveData.shared.redis_client import live_data_redis
from ActAndPos.models import Account, Position
from .tokens import ensure_valid_access_token

logger = logging.getLogger(__name__)

ACCOUNT_NUMBERS_CACHE_KEY = "live_data:schwab:account_numbers"
ACCOUNT_NUMBERS_CACHE_TTL = 60  # seconds
BALANCES_SNAPSHOT_KEY = "live_data:schwab:balances:{account_hash}"
POSITIONS_SNAPSHOT_KEY = "live_data:schwab:positions:{account_hash}"


class SchwabTraderAPI:
    BASE_URL = "https://api.schwabapi.com/trader/v1"
    
    def __init__(self, user):
        self.user = user
        connection = getattr(user, "schwab_token", None)
        if not connection:
            raise RuntimeError("User does not have an active Schwab connection.")

        self.token = ensure_valid_access_token(connection)
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token.access_token}",
            "Accept": "application/json"
        }

    def _request(self, method: str, path: str, *, retry_on_unauthorized: bool = True, **kwargs):
        # Normalize path to avoid double prefixing when BASE_URL already has /trader/v1
        path_clean = (path or "").lstrip("/")
        base = self.BASE_URL.rstrip("/")
        if base.endswith("/trader/v1") and path_clean.startswith("trader/v1/"):
            path_clean = path_clean[len("trader/v1/"):]
        url = f"{base}/{path_clean}"
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("timeout", 10)

        response = requests.request(method, url, headers=self._get_headers(), **request_kwargs)

        if response.status_code == 401 and retry_on_unauthorized:
            logger.warning("Schwab API 401 for %s %s — attempting token refresh", method, path)
            self.token = ensure_valid_access_token(self.user.schwab_token, force_refresh=True)
            response = requests.request(
                method,
                url,
                headers=self._get_headers(),
                **request_kwargs,
            )

        response.raise_for_status()
        return response

    @staticmethod
    def _looks_like_hash(value: str) -> bool:
        if not value:
            return False
        value = str(value).strip()
        return bool(re.fullmatch(r"[A-Fa-f0-9]{32,128}", value))

    @staticmethod
    def _looks_like_account_number(value: str) -> bool:
        if not value:
            return False
        value = str(value).strip()
        return value.isdigit() and 6 <= len(value) <= 12

    def fetch_account_numbers_map(self) -> Dict[str, str]:
        """Return mapping of accountNumber -> hashValue from /accounts/accountNumbers."""
        # Try cache first
        try:
            cached = live_data_redis.client.get(ACCOUNT_NUMBERS_CACHE_KEY)
            if cached:
                return loads(cached)
        except Exception as e:
            logger.debug("Schwab accountNumbers cache read failed: %s", e)

        mapping: Dict[str, str] = {}
        try:
            resp = self._request("GET", "/accounts/accountNumbers")
            data = resp.json() or []
            for row in data:
                number = str(row.get("accountNumber") or "").strip()
                hash_val = str(row.get("hashValue") or "").strip()
                if number and hash_val:
                    mapping[number] = hash_val

            try:
                live_data_redis.client.set(ACCOUNT_NUMBERS_CACHE_KEY, dumps(mapping), ex=ACCOUNT_NUMBERS_CACHE_TTL)
            except Exception as e:
                logger.debug("Schwab accountNumbers cache write failed: %s", e)
        except Exception as e:
            logger.warning("Schwab accountNumbers fetch failed: %s", e, exc_info=True)
        return mapping

    def get_account_number_hash_map(self) -> Dict[str, str]:
        """Backward-compatible alias used by views."""
        return self.fetch_account_numbers_map()

    def resolve_account_hash(self, account_id: str) -> str:
        """Accept accountNumber or hashValue and return hashValue."""
        account_id = str(account_id).strip()
        if self._looks_like_hash(account_id):
            return account_id
        if self._looks_like_account_number(account_id):
            mapping = self.fetch_account_numbers_map()
            resolved = mapping.get(account_id)
            if resolved:
                return resolved
        raise ValueError(f"Unable to resolve account hash for account_id={account_id}")
    
    def fetch_accounts(self):
        logger.info("DEBUG: fetch_accounts() CALLED")
        response = self._request("GET", "/accounts")
        return response.json()
    
    def fetch_account_details(self, account_hash, include_positions=True):
        params = {"fields": "positions"} if include_positions else {}
        response = self._request("GET", f"/accounts/{account_hash}", params=params)
        return response.json()
    
    def get_account_summary(self, account_hash):
        data = self.fetch_account_details(account_hash)
        acct = data.get('securitiesAccount', {})
        bal = acct.get('currentBalances', {}) or {}

        def _money(value):
            try:
                return f"${float(value):,.2f}"
            except Exception:
                return "$0.00"

        def _pct(value):
            try:
                return f"{float(value):.2f}%"
            except Exception:
                return "0.00%"

        return {
            'net_liquidating_value': _money(bal.get('liquidationValue', 0)),
            'stock_buying_power': _money(bal.get('stockBuyingPower', 0)),
            'option_buying_power': _money(bal.get('optionBuyingPower', 0)),
            'day_trading_buying_power': _money(bal.get('dayTradingBuyingPower', 0)),
            'available_funds_for_trading': _money(bal.get('availableFunds', 0)),
            'long_stock_value': _money(bal.get('longMarketValue', 0)),
            'equity_percentage': _pct(bal.get('equity', 0))
        }

    def _get_account_record(self, account_hash: str) -> Optional[Account]:
        return (
            Account.objects.filter(
                user=self.user, broker="SCHWAB", broker_account_id=account_hash
            )
            .select_related("user")
            .first()
        )

    def _cache_positions_snapshot(self, account_hash: str, positions: List[Dict]) -> None:
        try:
            key = POSITIONS_SNAPSHOT_KEY.format(account_hash=account_hash)
            live_data_redis.set_json(key, {"account_hash": account_hash, "positions": positions}, ex=300)
        except Exception as e:
            logger.debug("Schwab positions cache write failed for %s: %s", account_hash, e)

    def _get_positions_snapshot(self, account_hash: str) -> List[Dict]:
        try:
            key = POSITIONS_SNAPSHOT_KEY.format(account_hash=account_hash)
            raw = live_data_redis.client.get(key)
            if not raw:
                return []
            data = loads(raw)
            return data.get("positions", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.debug("Schwab positions cache read failed for %s: %s", account_hash, e)
            return []

    def _cache_balances_snapshot(self, account_hash: str, payload: Dict) -> None:
        try:
            key = BALANCES_SNAPSHOT_KEY.format(account_hash=account_hash)
            live_data_redis.set_json(key, payload, ex=300)
        except Exception as e:
            logger.debug("Schwab balances cache write failed for %s: %s", account_hash, e)

    def _get_balances_snapshot(self, account_hash: str) -> Dict:
        try:
            key = BALANCES_SNAPSHOT_KEY.format(account_hash=account_hash)
            raw = live_data_redis.client.get(key)
            if not raw:
                return {}
            data = loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.debug("Schwab balances cache read failed for %s: %s", account_hash, e)
            return {}

    def fetch_positions(self, account_hash: str) -> List[Dict]:
        """Fetch positions for an account (hash or accountNumber), persist, publish."""
        account_hash = self.resolve_account_hash(account_hash)
        try:
            data = self.fetch_account_details(account_hash, include_positions=True)
            acct = data.get("securitiesAccount", {}) or {}
            raw_positions = acct.get("positions", []) or []
        except Exception as e:
            logger.error("Failed live Schwab positions for %s: %s", account_hash, e)
            return self._get_positions_snapshot(account_hash)

        account = self._get_account_record(account_hash)
        if not account:
            logger.warning("Schwab account %s not registered in Thor", account_hash)
            return []

        normalized: List[Dict] = []

        for pos in raw_positions:
            instrument = pos.get("instrument", {}) or {}
            symbol = instrument.get("symbol") or instrument.get("underlyingSymbol")
            if not symbol:
                continue

            raw_asset = (instrument.get("assetType") or "EQ").upper()
            asset_type = "EQ" if raw_asset in {"EQ", "EQUITY"} else raw_asset

            long_qty = Decimal(str(pos.get("longQuantity") or 0))
            short_qty = Decimal(str(pos.get("shortQuantity") or 0))
            quantity = long_qty - short_qty

            avg_price = Decimal(str(pos.get("averagePrice") or 0))
            market_value = Decimal(str(pos.get("marketValue") or 0))
            mark_price = Decimal("0")
            if quantity:
                try:
                    mark_price = market_value / quantity
                except Exception:
                    mark_price = Decimal("0")

            position, _ = Position.objects.update_or_create(
                account=account,
                symbol=symbol,
                asset_type=asset_type,
                defaults={
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "mark_price": mark_price,
                },
            )

            payload = {
                "symbol": symbol,
                "asset_type": asset_type,
                "quantity": float(quantity),
                "avg_price": float(avg_price),
                "mark_price": float(position.mark_price),
                "market_value": float(position.market_value),
            }

            normalized.append(payload)

            try:
                live_data_redis.publish_position(account_hash, payload)
            except Exception as e:
                logger.error("Failed to publish Schwab position for %s: %s", symbol, e)

        self._cache_positions_snapshot(account_hash, normalized)
        return normalized

    def fetch_balances(self, account_id: str) -> Dict:
        """Fetch balances (accountNumber or hashValue), persist, and publish to Redis."""
        try:
            account_hash = self.resolve_account_hash(account_id)
        except Exception as e:
            logger.error("Failed to resolve Schwab account hash: %s", e)
            return {}

        try:
            data = self.fetch_account_details(account_hash, include_positions=False)
        except Exception as e:
            logger.error("Failed to fetch Schwab balances for %s: %s", account_hash, e)
            cached = self._get_balances_snapshot(account_hash)
            if cached:
                return cached
            return {}

        sec = (data.get("securitiesAccount", {}) or {})
        bal = (
            sec.get("currentBalances")
            or sec.get("initialBalances")
            or sec.get("balances")
            or {}
        )

        account_number = sec.get("accountNumber")

        def _dec(value, default=Decimal("0")):
            try:
                return Decimal(str(value if value is not None else default))
            except Exception:
                return default

        def _pick_first(*values):
            for candidate in values:
                if candidate is not None:
                    return candidate
            return Decimal("0")

        net_liq = bal.get("liquidationValue") or bal.get("netLiquidation") or 0
        stock_bp = (
            bal.get("stockBuyingPower")
            or bal.get("buyingPower")
            or bal.get("cashBuyingPower")
            or 0
        )
        option_bp = bal.get("optionBuyingPower") or 0
        daytrade_bp = bal.get("dayTradingBuyingPower") or 0
        avail = (
            bal.get("cashAvailableForTrading")
            or bal.get("availableFunds")
            or bal.get("availableFundsForTrading")
            or bal.get("availableFundsForTradingEquity")
            or 0
        )

        long_stock_value = (
            bal.get("longMarketValue")
            or bal.get("longStockValue")
            or bal.get("longMarginValue")
            or 0
        )

        equity_pct_raw = bal.get("equityPercentage")

        payload: Dict = {
            "account_hash": account_hash,
            "account_number": account_number,
            "net_liq": float(net_liq or 0),
            "stock_buying_power": float(stock_bp or 0),
            "option_buying_power": float(option_bp or 0),
            "day_trading_buying_power": float(daytrade_bp or 0),
            "available_funds_for_trading": float(avail or 0),
            "long_stock_value": float(long_stock_value or 0),
            "equity_percentage": float(equity_pct_raw or 0),
        }

        account = self._get_account_record(account_hash)
        if not account:
            display_name = account_number or account_hash
            account = Account.objects.create(
                user=self.user,
                broker="SCHWAB",
                broker_account_id=account_hash,
                account_number=account_number,
                display_name=display_name,
                currency="USD",
            )

        account.cash = _dec(bal.get("cashBalance") or bal.get("cashAvailableForTrading") or avail)
        account.current_cash = account.cash
        account.net_liq = _dec(net_liq)
        equity_val = bal.get("equity", account.net_liq)
        account.equity = _dec(equity_val, account.net_liq)
        account.stock_buying_power = _dec(stock_bp)
        account.option_buying_power = _dec(option_bp)
        account.day_trading_buying_power = _dec(daytrade_bp)
        if account_number:
            account.account_number = account_number
        long_stock_value_dec = _dec(long_stock_value)
        equity_pct_dec = _dec(equity_pct_raw) if equity_pct_raw is not None else Decimal("0")
        if equity_pct_raw is None and account.net_liq:
            try:
                equity_pct_dec = (account.equity / account.net_liq) * Decimal("100")
            except Exception:
                equity_pct_dec = Decimal("0")
        account.save(update_fields=[
            "cash",
            "current_cash",
            "net_liq",
            "equity",
            "stock_buying_power",
            "option_buying_power",
            "day_trading_buying_power",
            "account_number",
            "updated_at",
        ])

        payload["equity_percentage"] = float(equity_pct_dec)
        payload["long_stock_value"] = float(long_stock_value_dec)

        publish_key = account_hash or account_number
        try:
            live_data_redis.publish_balance(publish_key, payload)
        except Exception as e:
            logger.error("Failed to publish Schwab balances for %s: %s", publish_key, e)

        self._cache_balances_snapshot(account_hash, payload)
        return payload
