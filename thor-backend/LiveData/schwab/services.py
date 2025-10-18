"""
Schwab Trading API client.
"""

import logging
import requests
from typing import Dict, List
from decimal import Decimal

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
        bal = acct.get('currentBalances', {})
        return {
            'net_liquidating_value': f"${bal.get('liquidationValue', 0):,.2f}",
            'stock_buying_power': f"${bal.get('stockBuyingPower', 0):,.2f}",
            'option_buying_power': f"${bal.get('optionBuyingPower', 0):,.2f}",
            'day_trading_buying_power': f"${bal.get('dayTradingBuyingPower', 0):,.2f}",
            'available_funds_for_trading': f"${bal.get('availableFunds', 0):,.2f}",
            'long_stock_value': f"${bal.get('longMarketValue', 0):,.2f}",
            'equity_percentage': f"{bal.get('equity', 0):.2f}%"
        }
