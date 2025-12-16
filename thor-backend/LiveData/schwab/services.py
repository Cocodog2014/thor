"""
Schwab Trading API client.
"""

import logging
import requests
from typing import Dict, List, Optional
from decimal import Decimal

from LiveData.shared.redis_client import live_data_redis
from ActAndPos.models import Account, Position

logger = logging.getLogger(__name__)


class SchwabTraderAPI:
    BASE_URL = "https://api.schwabapi.com/trader/v1"
    
    def __init__(self, user):
        self.user = user
        self.token = user.schwab_token
        if not self.token:
            raise RuntimeError("User does not have an active Schwab connection.")
        if self.token.is_expired:
            logger.warning("Schwab access token expired for %s", user.email)
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token.access_token}",
            "Accept": "application/json"
        }
    
    def fetch_accounts(self):
        url = f"{self.BASE_URL}/accounts"
        response = requests.get(url, headers=self._get_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    
    def fetch_account_details(self, account_hash, include_positions=True):
        url = f"{self.BASE_URL}/accounts/{account_hash}"
        params = {"fields": "positions"} if include_positions else {}
        response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
        response.raise_for_status()
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

    def fetch_positions(self, account_hash: str) -> List[Dict]:
        """Fetch positions for an account, persist them, and publish to Redis."""
        data = self.fetch_account_details(account_hash, include_positions=True)
        acct = data.get("securitiesAccount", {}) or {}
        raw_positions = acct.get("positions", []) or []

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

        return normalized

    def _find_account_snapshot(self, account_number: str) -> Optional[Dict]:
        accounts = self.fetch_accounts() or []
        for acct in accounts:
            sec = (acct or {}).get("securitiesAccount", {}) or {}
            number = sec.get("accountNumber")
            if number is None:
                continue
            if str(number) == str(account_number):
                return acct
        return None

    def fetch_balances(self, account_number: str) -> Dict:
        """Fetch balances for an account_number, persist them, and publish to Redis."""
        snapshot = self._find_account_snapshot(account_number)
        if not snapshot:
            logger.warning("Schwab account %s not found in /accounts payload", account_number)
            return {}

        sec = (snapshot or {}).get("securitiesAccount", {}) or {}
        bal = (sec.get("currentBalances", {}) or {})

        account = self._get_account_record(account_number)
        if not account:
            logger.warning("Schwab account %s not registered in Thor", account_number)
            return {}

        def _dec(value, default=Decimal("0")):
            try:
                return Decimal(str(value if value is not None else default))
            except Exception:
                return default

        account.cash = _dec(bal.get("cashBalance"))
        account.current_cash = account.cash
        account.net_liq = _dec(bal.get("liquidationValue"))
        equity_val = bal.get("equity", account.net_liq)
        account.equity = _dec(equity_val, account.net_liq)
        account.stock_buying_power = _dec(bal.get("stockBuyingPower", bal.get("buyingPower")))
        account.option_buying_power = _dec(bal.get("optionBuyingPower"))
        account.day_trading_buying_power = _dec(bal.get("dayTradingBuyingPower"))
        account.save(update_fields=[
            "cash",
            "current_cash",
            "net_liq",
            "equity",
            "stock_buying_power",
            "option_buying_power",
            "day_trading_buying_power",
            "updated_at",
        ])

        payload: Dict = {
            "cash": float(account.cash),
            "net_liq": float(account.net_liq),
            "equity": float(account.equity),
            "stock_buying_power": float(account.stock_buying_power),
            "option_buying_power": float(account.option_buying_power),
            "day_trading_buying_power": float(account.day_trading_buying_power),
        }

        try:
            live_data_redis.publish_balance(account_number, payload)
        except Exception as e:
            logger.error("Failed to publish Schwab balances for %s: %s", account_number, e)

        return payload
