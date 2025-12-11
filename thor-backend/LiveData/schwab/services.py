"""
Schwab Trading API client.
"""

import logging
import requests
from typing import Dict, List
from decimal import Decimal

from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class SchwabTraderAPI:
    BASE_URL = "https://api.schwabapi.com/trader/v1"
    
    def __init__(self, user):
        self.user = user
        self.token = user.schwab_token
        if self.token.is_expired:
            logger.warning(f"Access token expired")
    
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

    def fetch_positions(self, account_hash: str) -> List[Dict]:
        """
        Fetch positions for an account and publish them to Redis.
        """
        data = self.fetch_account_details(account_hash, include_positions=True)
        acct = data.get("securitiesAccount", {}) or {}
        raw_positions = acct.get("positions", []) or []

        normalized: List[Dict] = []

        for pos in raw_positions:
            instrument = pos.get("instrument", {}) or {}
            symbol = instrument.get("symbol") or instrument.get("underlyingSymbol")
            asset_type = instrument.get("assetType")

            long_qty = pos.get("longQuantity") or 0
            short_qty = pos.get("shortQuantity") or 0
            quantity = Decimal(str(long_qty or 0)) - Decimal(str(short_qty or 0))

            avg_price = Decimal(str(pos.get("averagePrice", 0) or 0))
            market_value = Decimal(str(pos.get("marketValue", 0) or 0))

            position_payload = {
                "symbol": symbol,
                "asset_type": asset_type,
                "quantity": float(quantity),
                "average_price": float(avg_price),
                "market_value": float(market_value),
                "raw_position": pos,
            }

            normalized.append(position_payload)

            try:
                live_data_redis.publish_position(account_hash, position_payload)
            except Exception as e:
                logger.error(f"Failed to publish Schwab position for {symbol}: {e}")

        return normalized

    def fetch_balances(self, account_hash: str) -> Dict:
        """
        Fetch balances for an account and publish them to Redis.
        """
        data = self.fetch_account_details(account_hash, include_positions=False)

        acct = data.get("securitiesAccount", {}) or {}
        bal = acct.get("currentBalances", {}) or {}

        def _num(key, default=0):
            try:
                return float(bal.get(key, default) or 0)
            except Exception:
                return float(default)

        balance_payload: Dict = {
            "cash": _num("cashBalance"),
            "available_funds": _num("availableFunds"),
            "buying_power": _num("buyingPower") or _num("stockBuyingPower"),
            "liquidation_value": _num("liquidationValue"),
            "long_market_value": _num("longMarketValue"),
            "short_market_value": _num("shortMarketValue"),
            "equity": _num("equity"),
            "raw_balances": bal,
        }

        try:
            live_data_redis.publish_balance(account_hash, balance_payload)
        except Exception as e:
            logger.error(f"Failed to publish Schwab balances for {account_hash}: {e}")

        return balance_payload
