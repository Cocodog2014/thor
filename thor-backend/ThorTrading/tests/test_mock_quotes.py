"""Tests for mock quote generator."""

from decimal import Decimal
from django.test import TestCase
from ThorTrading.tests.mock_quotes import (
    MockQuoteGenerator,
    mock_quotes,
    mock_quotes_with_composite,
)


class MockQuoteGeneratorTests(TestCase):
    def setUp(self):
        self.generator = MockQuoteGenerator()

    def test_generate_single_quote(self):
        """Test generating a single enriched quote."""
        quote = self.generator.generate_quote("YM", Decimal("42100"))
        
        self.assertEqual(quote["instrument"]["symbol"], "/YM")
        self.assertEqual(quote["last"], "42100")
        self.assertIn("bid", quote)
        self.assertIn("ask", quote)
        self.assertIn("extended_data", quote)
        self.assertEqual(quote["extended_data"]["signal"], "BUY")

    def test_generate_batch(self):
        """Test generating a batch of quotes for all futures."""
        quotes = self.generator.generate_batch()
        
        self.assertEqual(len(quotes), 11)  # All 11 futures
        symbols = [q["instrument"]["symbol"] for q in quotes]
        self.assertIn("/YM", symbols)
        self.assertIn("/ES", symbols)
        self.assertNotIn("/TOTAL", symbols)  # TOTAL not in batch

    def test_custom_price_overrides(self):
        """Test custom price overrides."""
        quotes = self.generator.generate_batch(
            price_overrides={"YM": Decimal("100"), "ES": Decimal("200")}
        )
        
        ym_quote = next(q for q in quotes if q["instrument"]["symbol"] == "/YM")
        es_quote = next(q for q in quotes if q["instrument"]["symbol"] == "/ES")
        
        self.assertEqual(ym_quote["last"], "100")
        self.assertEqual(es_quote["last"], "200")

    def test_signal_overrides(self):
        """Test custom signal overrides."""
        quotes = self.generator.generate_batch(
            signal_overrides={"YM": "STRONG_SELL", "ES": "HOLD"}
        )
        
        ym_quote = next(q for q in quotes if q["instrument"]["symbol"] == "/YM")
        es_quote = next(q for q in quotes if q["instrument"]["symbol"] == "/ES")
        
        self.assertEqual(ym_quote["extended_data"]["signal"], "STRONG_SELL")
        self.assertEqual(es_quote["extended_data"]["signal"], "HOLD")

    def test_generate_with_composite(self):
        """Test composite signal calculation."""
        quotes, composite = self.generator.generate_with_composite()
        
        self.assertEqual(len(quotes), 11)
        self.assertIn("avg_weighted", composite)
        self.assertIn("composite_signal", composite)
        self.assertIn("count", composite)
        self.assertEqual(composite["count"], 11)
        self.assertIn(composite["composite_signal"], ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"])

    def test_composite_strong_buy(self):
        """Test STRONG_BUY composite when avg >= 1.5."""
        signals = {f: "STRONG_BUY" for f in self.generator.FUTURES}
        _, composite = self.generator.generate_with_composite(signal_overrides=signals)
        
        self.assertEqual(composite["composite_signal"], "STRONG_BUY")
        self.assertEqual(composite["signal_weight_sum"], 22)  # 11 * 2

    def test_composite_strong_sell(self):
        """Test STRONG_SELL composite when avg <= -1.5."""
        signals = {f: "STRONG_SELL" for f in self.generator.FUTURES}
        _, composite = self.generator.generate_with_composite(signal_overrides=signals)
        
        self.assertEqual(composite["composite_signal"], "STRONG_SELL")
        self.assertEqual(composite["signal_weight_sum"], -22)

    def test_composite_hold(self):
        """Test HOLD composite when avg near zero."""
        signals = {f: "HOLD" for f in self.generator.FUTURES}
        _, composite = self.generator.generate_with_composite(signal_overrides=signals)
        
        self.assertEqual(composite["composite_signal"], "HOLD")
        self.assertEqual(composite["signal_weight_sum"], 0)

    def test_simulate_price_movement(self):
        """Test price movement simulation."""
        ticks = [Decimal("5"), Decimal("10"), Decimal("-3"), Decimal("2")]
        quotes = self.generator.simulate_price_movement("YM", Decimal("100"), ticks)
        
        self.assertEqual(len(quotes), 4)
        self.assertEqual(quotes[0]["last"], "105")
        self.assertEqual(quotes[1]["last"], "115")
        self.assertEqual(quotes[2]["last"], "112")
        self.assertEqual(quotes[3]["last"], "114")

    def test_simulate_intraday_session(self):
        """Test full intraday session simulation."""
        session = self.generator.simulate_intraday_session(
            futures=["YM", "ES"],
            volatility=Decimal("1.0"),
            num_ticks=5,
        )
        
        self.assertEqual(len(session), 5)  # 5 ticks
        self.assertEqual(len(session[0]), 2)  # 2 futures per tick
        
        # Verify prices change across ticks
        ym_prices = [
            Decimal(tick[0]["last"])
            for tick in session
            if tick[0]["instrument"]["symbol"] == "/YM"
        ]
        self.assertNotEqual(ym_prices[0], ym_prices[-1])  # Prices moved

    def test_convenience_functions(self):
        """Test convenience factory functions."""
        quotes = mock_quotes({"YM": Decimal("100")})
        self.assertEqual(len(quotes), 11)
        
        quotes, composite = mock_quotes_with_composite({"YM": Decimal("100")})
        self.assertEqual(len(quotes), 11)
        self.assertIn("composite_signal", composite)

