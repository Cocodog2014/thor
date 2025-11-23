"""Mock quote generator for testing market metrics without live data.

Provides realistic enriched quote structures matching the format returned by
get_enriched_quotes_with_composite() for testing purposes.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional


class MockQuoteGenerator:
    """Generate mock enriched quotes for testing."""

    FUTURES = ["YM", "ES", "NQ", "RTY", "CL", "SI", "HG", "GC", "VX", "DX", "ZB"]
    
    def __init__(self, base_prices: Optional[Dict[str, Decimal]] = None):
        """Initialize with optional base prices for each future.
        
        Args:
            base_prices: Dict mapping future symbol to base price (e.g., {"YM": 100, "ES": 200})
        """
        self.base_prices = base_prices or {
            "YM": Decimal("42000"),
            "ES": Decimal("5000"),
            "NQ": Decimal("18000"),
            "RTY": Decimal("2100"),
            "CL": Decimal("70"),
            "SI": Decimal("25"),
            "HG": Decimal("4"),
            "GC": Decimal("2000"),
            "VX": Decimal("15"),
            "DX": Decimal("103"),
            "ZB": Decimal("110"),
        }
        self.signals = {
            "YM": "BUY",
            "ES": "STRONG_BUY",
            "NQ": "SELL",
            "RTY": "HOLD",
            "CL": "BUY",
            "SI": "STRONG_SELL",
            "HG": "BUY",
            "GC": "SELL",
            "VX": "HOLD",
            "DX": "BUY",
            "ZB": "STRONG_BUY",
        }
        self.weights = {
            "STRONG_BUY": 2,
            "BUY": 1,
            "HOLD": 0,
            "SELL": -1,
            "STRONG_SELL": -2,
        }

    def generate_quote(
        self,
        future: str,
        last_price: Decimal,
        move_percent: Decimal = Decimal("0"),
        signal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single enriched quote for a future.
        
        Args:
            future: Future symbol (e.g., "YM")
            last_price: Current last price
            move_percent: Percentage move from base price (for open_prev calculations)
            signal: Override signal (defaults to predefined signal)
        
        Returns:
            Enriched quote dict matching get_enriched_quotes_with_composite format
        """
        signal = signal or self.signals.get(future, "HOLD")
        spread = last_price * Decimal("0.0001")  # 1 bp spread
        bid = last_price - (spread / 2)
        ask = last_price + (spread / 2)
        
        base = self.base_prices.get(future, last_price)
        open_price = base * (1 + move_percent / 100)
        prev_close = base
        
        return {
            "instrument": {
                "symbol": f"/{future}",
                "description": f"{future} Future",
            },
            "last": str(last_price),
            "bid": str(bid),
            "ask": str(ask),
            "bid_size": 10,
            "ask_size": 10,
            "volume": 50000 + int(last_price),
            "vwap": str(last_price * Decimal("0.999")),
            "spread": str(spread),
            "open_price": str(open_price),
            "close_price": str(prev_close),
            "previous_close": str(prev_close),
            "open_prev_diff": str(open_price - prev_close),
            "open_prev_pct": str((open_price - prev_close) / prev_close * 100),
            "low_price": str(last_price * Decimal("0.995")),
            "high_price": str(last_price * Decimal("1.005")),
            "range_diff": str(last_price * Decimal("0.01")),
            "range_pct": str(Decimal("1.0")),
            "extended_data": {
                "signal": signal,
                "signal_weight": self.weights.get(signal, 0),
                "low_52w": str(last_price * Decimal("0.8")),
                "high_52w": str(last_price * Decimal("1.2")),
            },
        }

    def generate_batch(
        self,
        price_overrides: Optional[Dict[str, Decimal]] = None,
        signal_overrides: Optional[Dict[str, str]] = None,
        futures: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate a batch of enriched quotes for multiple futures.
        
        Args:
            price_overrides: Dict mapping future to custom last price
            signal_overrides: Dict mapping future to custom signal
            futures: List of futures to include (defaults to all 11)
        
        Returns:
            List of enriched quote dicts
        """
        futures = futures or self.FUTURES
        price_overrides = price_overrides or {}
        signal_overrides = signal_overrides or {}
        
        quotes = []
        for future in futures:
            last_price = price_overrides.get(future, self.base_prices.get(future, Decimal("100")))
            signal = signal_overrides.get(future)
            quotes.append(self.generate_quote(future, last_price, signal=signal))
        
        return quotes

    def generate_with_composite(
        self,
        price_overrides: Optional[Dict[str, Decimal]] = None,
        signal_overrides: Optional[Dict[str, str]] = None,
        futures: Optional[List[str]] = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate enriched quotes plus TOTAL composite matching service format.
        
        Returns:
            Tuple of (enriched_quotes, composite_dict)
        """
        quotes = self.generate_batch(price_overrides, signal_overrides, futures)
        
        # Calculate composite
        total_weight = sum(
            self.weights.get(q["extended_data"]["signal"], 0) for q in quotes
        )
        count = len(quotes)
        avg_weighted = Decimal(total_weight) / Decimal(count) if count else Decimal("0")
        
        # Determine composite signal
        if avg_weighted >= 1.5:
            composite_signal = "STRONG_BUY"
        elif avg_weighted >= 0.5:
            composite_signal = "BUY"
        elif avg_weighted <= -1.5:
            composite_signal = "STRONG_SELL"
        elif avg_weighted <= -0.5:
            composite_signal = "SELL"
        else:
            composite_signal = "HOLD"
        
        composite = {
            "avg_weighted": float(avg_weighted),
            "count": count,
            "composite_signal": composite_signal,
            "signal_weight_sum": total_weight,
        }
        
        return quotes, composite

    def simulate_price_movement(
        self,
        future: str,
        start_price: Decimal,
        ticks: List[Decimal],
    ) -> List[Dict[str, Any]]:
        """Simulate price movement over multiple ticks for a single future.
        
        Args:
            future: Future symbol
            start_price: Starting price
            ticks: List of price adjustments (e.g., [+5, +10, -3] for movement)
        
        Returns:
            List of enriched quotes showing price progression
        """
        quotes = []
        current_price = start_price
        
        for adjustment in ticks:
            current_price += adjustment
            quotes.append(self.generate_quote(future, current_price))
        
        return quotes

    def simulate_intraday_session(
        self,
        futures: Optional[List[str]] = None,
        volatility: Decimal = Decimal("0.5"),
        num_ticks: int = 10,
    ) -> List[List[Dict[str, Any]]]:
        """Simulate a full intraday session with realistic price movements.
        
        Args:
            futures: Futures to simulate (defaults to all)
            volatility: Percentage volatility per tick (e.g., 0.5 = ±0.5%)
            num_ticks: Number of intraday ticks to generate
        
        Returns:
            List of quote batches (one per tick)
        """
        import random
        futures = futures or self.FUTURES
        
        session_quotes = []
        current_prices = {f: self.base_prices.get(f, Decimal("100")) for f in futures}
        
        for _ in range(num_ticks):
            # Random walk with volatility
            for future in futures:
                change_pct = Decimal(random.uniform(-float(volatility), float(volatility)))
                current_prices[future] *= (1 + change_pct / 100)
            
            batch = self.generate_batch(price_overrides=current_prices, futures=futures)
            session_quotes.append(batch)
        
        return session_quotes


# Convenience factory functions
def mock_quotes(price_overrides: Optional[Dict[str, Decimal]] = None) -> List[Dict[str, Any]]:
    """Quick mock quote batch for testing."""
    gen = MockQuoteGenerator()
    return gen.generate_batch(price_overrides=price_overrides)


def mock_quotes_with_composite(
    price_overrides: Optional[Dict[str, Decimal]] = None
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Quick mock quotes + composite for testing."""
    gen = MockQuoteGenerator()
    return gen.generate_with_composite(price_overrides=price_overrides)
