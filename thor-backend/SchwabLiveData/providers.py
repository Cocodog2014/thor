"""
Data Provider System for SchwabLiveData

This module provides an abstraction layer for market data providers.
- JSONProvider: Uses a JSON file for fake futures data (development/testing)
- SchwabProvider: Placeholder for real Schwab API integration (future)

The provider system allows easy switching between data sources without
changing the rest of the application.
"""

import json
import os
import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from openpyxl import load_workbook
import threading

# Import Excel Live provider from dedicated module to avoid duplication
try:
    from .excel_live import ExcelLiveProvider  # type: ignore
except Exception:
    ExcelLiveProvider = None  # Optional dependency; factory will raise if requested



class BaseProvider(ABC):
    """Abstract base class for all market data providers."""
    
    @abstractmethod
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Return latest market data for the given symbols.
        
        Args:
            symbols: List of instrument symbols (e.g., ['/YM', '/ES', '/NQ'])
            
        Returns:
            List of market data dictionaries matching the API schema
        """
        raise NotImplementedError()
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Return provider health status and metadata.
        
        Returns:
            Dictionary with provider status, connection info, rate limits, etc.
        """
        raise NotImplementedError()
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        raise NotImplementedError()


class JSONProvider(BaseProvider):
    """
    Provider that reads fake futures data from a JSON file.
    
    This provider simulates live market data by:
    1. Loading base data from JSON file
    2. Adding realistic price variations
    3. Rotating through different signals
    4. Updating timestamps
    
    The JSON file can be easily modified or replaced when switching
    to real Schwab API data.
    """
    
    def __init__(self, json_file_path: str, enable_live_simulation: bool = True):
        self.json_file_path = json_file_path
        self.enable_live_simulation = enable_live_simulation
        self._last_update = None
        self._iteration_count = 0
        self._random = random.Random(42)  # Fixed seed for consistent dev behavior
        
        # Load base data from JSON
        self._base_data = self._load_json_data()
        
    def _load_json_data(self) -> Dict[str, Any]:
        """Load the base futures data from JSON file."""
        try:
            with open(self.json_file_path, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Return empty data if file doesn't exist
            return {"futures": []}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.json_file_path}: {e}")
    
    def _simulate_live_price(self, base_price: float, symbol: str) -> Dict[str, float]:
        """
        Simulate realistic price movements from base price.
        
        Args:
            base_price: The base price from JSON
            symbol: The instrument symbol (affects volatility)
            
        Returns:
            Dictionary with simulated bid, ask, last, high, low prices
        """
        # Different volatility by instrument type
        volatility_map = {
            '/YM': 5.0,    # Dow futures - moderate volatility
            '/ES': 2.0,    # S&P 500 futures - moderate volatility  
            '/NQ': 8.0,    # Nasdaq futures - higher volatility
            'RTY': 4.0,    # Russell 2000 - higher volatility
            'CL': 0.5,     # Crude oil - moderate volatility
            'SI': 0.15,    # Silver - moderate volatility
            'HG': 0.02,    # Copper - lower volatility
            'GC': 8.0,     # Gold - moderate volatility
            'VX': 0.8,     # VIX - high volatility
            'DX': 0.3,     # Dollar index - lower volatility
            'ZB': 0.5,     # 30Y Bond - moderate volatility
        }
        
        volatility = volatility_map.get(symbol, 1.0)
        
        # Generate price movement
        change_pct = self._random.gauss(0, 0.002)  # 0.2% std dev
        price_change = base_price * change_pct
        current_price = base_price + price_change
        
        # Add some intraday range
        daily_range = volatility * self._random.uniform(0.5, 2.0)
        high_price = current_price + (daily_range * 0.6)
        low_price = current_price - (daily_range * 0.4)
        
        # Bid/Ask spread (realistic spreads)
        spread_map = {
            '/YM': 1.0, '/ES': 0.25, '/NQ': 0.5, 'RTY': 0.1,
            'CL': 0.01, 'SI': 0.005, 'HG': 0.0005, 'GC': 0.1,
            'VX': 0.05, 'DX': 0.005, 'ZB': 0.015
        }
        spread = spread_map.get(symbol, 0.1)
        
        bid = current_price - (spread / 2)
        ask = current_price + (spread / 2)
        
        return {
            'last': round(current_price, 4),
            'bid': round(bid, 4),
            'ask': round(ask, 4),
            'high': round(high_price, 4),
            'low': round(low_price, 4)
        }
    
    def _rotate_signal(self, base_signal: str, symbol: str) -> str:
        """
        Simulate signal changes over time.
        
        Args:
            base_signal: The base signal from JSON
            symbol: The instrument symbol
            
        Returns:
            Current signal (may be different from base)
        """
        signals = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
        
        # Slow signal rotation (every ~10 iterations per symbol)
        symbol_hash = hash(symbol) % 1000
        rotation_cycle = (self._iteration_count + symbol_hash) // 10
        
        # 80% chance to keep base signal, 20% chance to use rotated signal
        if self._random.random() < 0.8:
            return base_signal
        else:
            signal_index = rotation_cycle % len(signals)
            return signals[signal_index]
    
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Get latest quotes for requested symbols from JSON data with live simulation.
        
        Args:
            symbols: List of symbols to fetch
            
        Returns:
            List of market data dictionaries
        """
        self._iteration_count += 1
        current_time = datetime.now(timezone.utc).isoformat()
        
        result = []
        
        for symbol in symbols:
            # Find the symbol in our JSON data
            base_future = None
            for future in self._base_data.get("futures", []):
                if future.get("symbol") == symbol:
                    base_future = future
                    break
            
            if not base_future:
                # If symbol not found in JSON, create a minimal entry
                base_future = {
                    "symbol": symbol,
                    "name": symbol,
                    "base_price": 100.0,
                    "signal": "HOLD",
                    "stat_value": 0.0,
                    "contract_weight": 1.0
                }
            
            # Get base values
            base_price = float(base_future.get("base_price", 100.0))
            base_signal = base_future.get("signal", "HOLD")
            stat_value = base_future.get("stat_value", 0.0)
            contract_weight = base_future.get("contract_weight", 1.0)
            
            # Simulate live prices if enabled
            if self.enable_live_simulation:
                prices = self._simulate_live_price(base_price, symbol)
                current_signal = self._rotate_signal(base_signal, symbol)
            else:
                # Use static prices from JSON
                prices = {
                    'last': base_price,
                    'bid': base_price - 0.25,
                    'ask': base_price + 0.25,
                    'high': base_price + 2.0,
                    'low': base_price - 2.0
                }
                current_signal = base_signal
            
            # Calculate derived values
            previous_close = base_price  # Simplified
            change = prices['last'] - previous_close
            change_percent = (change / previous_close) * 100 if previous_close else 0
            vwap = (prices['bid'] + prices['ask'] + prices['last']) / 3
            
            # Symbol-specific precision (same as ExcelProvider)
            precision_map = {
                '/YM': 0, 'YM': 0,  # Dow mini trades in whole points
                '/ES': 2, 'ES': 2,  # Quarter point increments
                '/NQ': 2, 'NQ': 2,  # Quarter point increments
                'RTY': 2,           # Tenth increments
                'CL': 2,            # Penny increments
                'SI': 3,            # Half-cent increments (0.005)
                'HG': 4,            # 0.0005 tick size
                'GC': 1,            # Dime increments
                'VX': 2,            # 0.01
                'DX': 2,            # 0.01
                'ZB': 2,            # 1/32 simplified to 2 decimals
            }
            display_precision = precision_map.get(symbol, 2)
            
            # Build market data entry
            market_data = {
                "instrument": {
                    "id": hash(symbol) % 10000,
                    "symbol": symbol,
                    "name": base_future.get("name", symbol),
                    "exchange": base_future.get("exchange", "CME"),
                    "currency": "USD",
                    "display_precision": display_precision,
                    "is_active": True,
                    "sort_order": symbols.index(symbol) if symbol in symbols else 999
                },
                "price": str(prices['last']),
                "bid": str(prices['bid']),
                "ask": str(prices['ask']),
                "last_size": self._random.randint(1, 50),
                "bid_size": self._random.randint(10, 100),
                "ask_size": self._random.randint(10, 100),
                "open_price": str(previous_close),
                "high_price": str(prices['high']),
                "low_price": str(prices['low']),
                "close_price": None,
                "previous_close": str(previous_close),
                "change": str(round(change, 4)),
                "change_percent": str(round(change_percent, 4)),
                "vwap": str(round(vwap, 4)),
                "volume": self._random.randint(50000, 500000),
                "market_status": "OPEN",
                "data_source": "json_provider",
                "is_real_time": self.enable_live_simulation,
                "delay_minutes": 0,
                "extended_data": {
                    "signal": current_signal,
                    "stat_value": str(stat_value),
                    "contract_weight": str(contract_weight)
                },
                "timestamp": current_time
            }
            
            result.append(market_data)
        
        self._last_update = current_time
        return result
    
    def health_check(self) -> Dict[str, Any]:
        """Return health status for JSON provider."""
        file_exists = os.path.exists(self.json_file_path)
        
        return {
            "provider": "json",
            "connected": file_exists,
            "json_file": self.json_file_path,
            "file_exists": file_exists,
            "live_simulation": self.enable_live_simulation,
            "last_update": self._last_update,
            "iteration_count": self._iteration_count
        }
    
    def get_provider_name(self) -> str:
        return "JSON Provider"


class SchwabProvider(BaseProvider):
    """
    Placeholder provider for Schwab API integration.
    
    This will be implemented when Schwab API credentials are available.
    For now, it raises NotImplementedError to clearly indicate it's not ready.
    """
    
    def __init__(self, config: Dict[str, Any]):
        from .schwab_client import SchwabApiClient  # Lazy import to keep dependency surface small
        self.config = config or {}
        self.client = SchwabApiClient(self.config)
        self._connected = False
        # Note: actual OAuth handshake will be performed when permissions are granted
    
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Schwab API.
        
        TODO: Implement when Schwab API access is available:
        1. Authenticate with OAuth2
        2. Make REST API calls to Schwab
        3. Map Schwab response fields to our standard schema
        4. Handle rate limits and errors
        """
        # The implementation will:
        # - Ensure valid access token (refresh if needed)
        # - Call quotes endpoint and transform response to our schema
        # For now, we raise 501 to signal upstream that the provider exists but is not yet enabled.
        raise NotImplementedError("Schwab API integration pending approval; provider scaffolded but not active.")
    
    def health_check(self) -> Dict[str, Any]:
        """Return health status for Schwab provider."""
        info = self.client.health()
        return {
            "provider": "schwab",
            "connected": info.get("configured", False) and self._connected,
            "status": info.get("status", "not_configured"),
            "auth": info.get("auth", {}),
            "base_url": self.config.get("base_url"),
            "scopes": self.config.get("scopes"),
        }
    
    def get_provider_name(self) -> str:
        return "Schwab API Provider (Not Implemented)"


def create_provider(provider_type: str, **kwargs) -> BaseProvider:
    """
    Factory function to create the appropriate provider.
    
    Args:
        provider_type: 'json' or 'schwab'
        **kwargs: Provider-specific configuration
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider_type is not supported
    """
    if provider_type.lower() == 'json':
        json_file = kwargs.get('json_file', 'futures_data.json')
        live_sim = kwargs.get('live_simulation', True)
        return JSONProvider(json_file, live_sim)
    
    elif provider_type.lower() == 'excel':
        excel_file = kwargs.get('excel_file')
        sheet_name = kwargs.get('sheet_name', 'Futures')
        live_sim = kwargs.get('live_simulation', True)
        return ExcelProvider(excel_file, sheet_name=sheet_name, enable_live_simulation=live_sim)
    
    elif provider_type.lower() == 'excel_live':
        if ExcelLiveProvider is None:
            raise RuntimeError("Excel Live provider requested but xlwings is not installed.")
        excel_file = kwargs.get('excel_file')
        sheet_name = kwargs.get('sheet_name', 'Futures')
        live_range = kwargs.get('live_range', 'A1:M16')
        poll_ms = int(kwargs.get('poll_ms', 150))
        require_open = bool(kwargs.get('require_open', False))
        prov = ExcelLiveProvider(
            file_path=excel_file,
            sheet_name=sheet_name,
            range_address=live_range,
            poll_ms=poll_ms,
            require_open=require_open,
        )
        # Start polling thread immediately
        if hasattr(prov, 'start'):
            prov.start()
        return prov
    
    elif provider_type.lower() == 'schwab':
        config = kwargs.get('config', {})
        return SchwabProvider(config)
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


class ExcelProvider(BaseProvider):
    """Provider that reads futures data from an Excel file (xlsx/xlsm)."""

    def __init__(self, excel_file_path: str, sheet_name: str = 'Futures', enable_live_simulation: bool = True):
        if not excel_file_path:
            raise ValueError("ExcelProvider requires 'excel_file_path'")
        self.excel_file_path = excel_file_path
        self.sheet_name = sheet_name
        self.enable_live_simulation = enable_live_simulation
        self._random = random.Random(99)
        self._last_update = None
        self._iteration_count = 0
        self._file_mtime = os.path.getmtime(self.excel_file_path) if os.path.exists(self.excel_file_path) else None
        self._base_rows = self._load_excel()

    def _load_excel(self) -> List[Dict[str, Any]]:
        try:
            wb = load_workbook(filename=self.excel_file_path, data_only=True, read_only=True)
            if self.sheet_name not in wb.sheetnames:
                # If sheet not found, use the first sheet
                ws = wb[wb.sheetnames[0]]
            else:
                ws = wb[self.sheet_name]

            # Expect a header row
            rows_iter = ws.iter_rows(values_only=True)
            headers = next(rows_iter)
            headers = [str(h).strip().lower() if h is not None else '' for h in headers]
            # If the first column header is blank, assume it's the symbol column
            if headers and headers[0] == '':
                headers[0] = 'symbol'

            data_rows = []
            for r in rows_iter:
                row = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                # Normalize keys used by our schema
                symbol = (row.get('symbol') or row.get('ticker') or row.get('sym'))
                if not symbol:
                    continue
                data_rows.append(row)
            return data_rows
        except FileNotFoundError:
            return []
        except Exception as e:
            raise RuntimeError(f"Error loading Excel file {self.excel_file_path}: {e}")

    def _coalesce(self, row: Dict[str, Any], keys: List[str], default=None):
        for k in keys:
            if k in row and row[k] is not None and row[k] != '':
                return row[k]
        return default

    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        # Helper to parse numbers that may be in fractional-tick format like 116'27 (== 116 + 27/32)
        def parse_numeric_value(v: Any) -> Optional[float]:
            if v is None:
                return None
            if isinstance(v, (int, float, Decimal)):
                try:
                    return float(v)
                except Exception:
                    return None
            s = str(v).strip()
            if s == '':
                return None
            # Remove commas
            s2 = s.replace(',', '')
            # Try simple float
            try:
                return float(s2)
            except Exception:
                pass
            # Try 32nds format: 116'27 or 116'27.5
            import re
            m = re.match(r"^(\d+)'(\d+(?:\.\d+)?)$", s2)
            if m:
                whole = float(m.group(1))
                frac = float(m.group(2)) / 32.0
                return whole + frac
            return None
        # Reload if the file changed to pick up fresh RTD-calculated values
        try:
            mtime = os.path.getmtime(self.excel_file_path)
            if self._file_mtime != mtime:
                self._base_rows = self._load_excel()
                self._file_mtime = mtime
        except Exception:
            pass

        self._iteration_count += 1
        now = datetime.now(timezone.utc).isoformat()
        result: List[Dict[str, Any]] = []

        # Build a map by symbol for quick lookup with aliases
        by_symbol: Dict[str, Dict[str, Any]] = {}
        alias_map = {
            # Common alternate tickers
            'RT': 'RTY',
            'RTY': 'RTY',
            '30YBOND': 'ZB',
            'ZB': 'ZB',
            'YM': '/YM', '/YM': '/YM',
            'ES': '/ES', '/ES': '/ES',
            'NQ': '/NQ', '/NQ': '/NQ',
        }
        for row in self._base_rows:
            sym_raw = self._coalesce(row, ['symbol', 'ticker', 'sym'])
            if sym_raw is None:
                continue
            sym = str(sym_raw).strip()
            if not sym:
                continue
            # Primary mapping as-is
            by_symbol[sym] = row
            # Add with/without leading slash variants for equity index futures
            if sym.startswith('/'):
                by_symbol[sym[1:]] = row
            else:
                by_symbol[f'/{sym}'] = row
            # Add alias if present
            alias = alias_map.get(sym.upper())
            if alias:
                by_symbol[alias] = row

        # Symbol-specific precision defaults (matches futures contract conventions)
        precision_defaults = {
            '/YM': 0, 'YM': 0,  # Dow mini trades in whole points
            '/ES': 2, 'ES': 2,  # Quarter point increments
            '/NQ': 2, 'NQ': 2,  # Quarter point increments
            'RTY': 2,           # Tenth increments
            'CL': 2,            # Penny increments
            'SI': 3,            # Half-cent increments (0.005)
            'HG': 4,            # 0.0005 tick size
            'GC': 1,            # Dime increments
            'VX': 2,            # 0.01
            'DX': 2,            # 0.01
            'ZB': 2,            # 1/32 simplified to 2 decimals
        }

        for symbol in symbols:
            row = by_symbol.get(symbol, {})
            name = self._coalesce(row, ['name', 'description'], symbol)
            exchange = self._coalesce(row, ['exchange', 'exch'], 'CME')
            # Use symbol-specific default or fallback to 2
            default_precision = precision_defaults.get(symbol, 2)
            display_precision = int(self._coalesce(row, ['display_precision', 'precision', 'dp'], default_precision))

            # Pull numeric fields (support various header names)
            def f(keys, default=None):
                v = self._coalesce(row, keys, None)
                val = parse_numeric_value(v)
                return val if val is not None else default

            base_price = f(['base_price', 'last', 'price'], None)
            bid = f(['bid'], None)
            ask = f(['ask'], None)
            high = f(['high', 'high_price', 'world high', 'whigh'], None)
            low = f(['low', 'low_price', 'world low', 'wlow'], None)
            open_price = f(['open', 'open_price'], None)
            prev_close = f(['previous_close', 'prev_close', 'close_prev', 'close'], None)
            vwap = f(['vwap'], None)
            # Volume can be integer; still try numeric parse
            volume = f(['volume', 'vol'], None)
            volume = int(volume) if volume is not None else None
            signal = self._coalesce(row, ['signal'], 'HOLD')
            # Extended numeric fields should always be numeric to satisfy enrichment step
            stat_value = f(['stat_value', 'stat'], 0.0)
            contract_weight = f(['contract_weight', 'weight'], 1.0)
            change_provided = f(['change', 'num', 'netchange', 'net change'], None)
            change_pct_provided = f(['change_percent', 'perc', 'change%'], None)
            bid_size = f(['bid_size', 'bidsize', 'bid size'], None)
            ask_size = f(['ask_size', 'asksize', 'ask size'], None)
            bid_size = int(bid_size) if bid_size is not None else None
            ask_size = int(ask_size) if ask_size is not None else None

            # Pricing logic with strict control over simulation
            # If live simulation is enabled, simulate a complete price set.
            # If disabled, do NOT fabricate values—use only what's provided in the sheet.
            if self.enable_live_simulation:
                jp = JSONProvider(json_file_path="", enable_live_simulation=True)
                prices = jp._simulate_live_price(base_price, symbol)
                bid = bid if bid is not None else prices['bid']
                ask = ask if ask is not None else prices['ask']
                high = high if high is not None else prices['high']
                low = low if low is not None else prices['low']
                last = prices['last']
                vwap = vwap if vwap is not None else ( (bid + ask + last) / 3 )
            else:
                # Use only provided values from the sheet
                last = base_price if base_price is not None else None
                # Keep bid/ask/high/low/vwap as-is; do not compute unless enough info exists
                if vwap is None and bid is not None and ask is not None and last is not None:
                    vwap = (bid + ask + last) / 3

            if change_provided is not None:
                change = change_provided
            else:
                change = (last - prev_close) if (last is not None and prev_close is not None) else None

            if change_pct_provided is not None:
                change_pct = change_pct_provided
            else:
                change_pct = ((change / prev_close) * 100) if (change is not None and prev_close not in (None, 0)) else None

            result.append({
                "instrument": {
                    "id": hash(symbol) % 10000,
                    "symbol": symbol,
                    "name": name,
                    "exchange": exchange,
                    "currency": "USD",
                    "display_precision": display_precision,
                    "is_active": True,
                    "sort_order": symbols.index(symbol),
                },
                "price": str(round(last, display_precision)) if last is not None else None,
                "bid": str(round(bid, display_precision)) if bid is not None else None,
                "ask": str(round(ask, display_precision)) if ask is not None else None,
                "last_size": None,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "open_price": str(open_price) if open_price is not None else None,
                "high_price": str(high) if high is not None else None,
                "low_price": str(low) if low is not None else None,
                "close_price": None,
                "previous_close": str(prev_close) if prev_close is not None else None,
                "change": str(round(change, 4)) if change is not None else None,
                "change_percent": str(round(change_pct, 4)) if change_pct is not None else None,
                "vwap": str(round(vwap, display_precision)) if vwap is not None else None,
                "volume": volume,
                "market_status": "OPEN",
                "data_source": "excel_provider",
                "is_real_time": self.enable_live_simulation,
                "delay_minutes": 0,
                "extended_data": {
                    "signal": signal,
                    "stat_value": str(stat_value),
                    "contract_weight": str(contract_weight),
                },
                "timestamp": now,
            })

        self._last_update = now
        return result

    def health_check(self) -> Dict[str, Any]:
        exists = os.path.exists(self.excel_file_path)
        return {
            "provider": "excel",
            "connected": exists,
            "excel_file": self.excel_file_path,
            "sheet": self.sheet_name,
            "last_update": self._last_update,
            "iteration_count": self._iteration_count,
        }

    def get_provider_name(self) -> str:
        return "Excel Provider"


## ExcelLiveProvider implementation moved to SchwabLiveData/excel_live.py