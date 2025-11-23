from decimal import Decimal
from django.test import TestCase
from FutureTrading.models.MarketSession import MarketSession
from FutureTrading.services.market_metrics import (
    MarketOpenMetric,
    MarketHighMetric,
    MarketLowMetric,
    MarketCloseMetric,
    MarketRangeMetric,
)


def make_session(country: str, future: str, session_number: int, last_price=None, market_open=None,
                 high=None, low=None):
    return MarketSession.objects.create(
        session_number=session_number,
        year=2025,
        month=11,
        date=22,
        day="Sat",
        country=country,
        future=future,
        last_price=last_price,
        market_open=market_open,
        market_high_number=high,
        market_low_number=low,
    )


class MarketOpenMetricTests(TestCase):
    def test_market_open_populates_from_last_price(self):
        ym = make_session("USA", "YM", 1, last_price=Decimal("100"))
        total = make_session("USA", "TOTAL", 1, last_price=Decimal("250"))

        updated = MarketOpenMetric.update(1)
        self.assertEqual(updated, 2)
        ym.refresh_from_db(); total.refresh_from_db()
        self.assertEqual(ym.market_open, Decimal("100"))
        self.assertEqual(total.market_open, Decimal("250"))

    def test_market_open_handles_total_composite_row(self):
        """Verify TOTAL row gets market_open just like individual futures."""
        for future in ["YM", "ES", "NQ", "TOTAL"]:
            make_session("USA", future, 2, last_price=Decimal("100"))
        updated = MarketOpenMetric.update(2)
        self.assertEqual(updated, 4)
        total = MarketSession.objects.get(country="USA", future="TOTAL", session_number=2)
        self.assertEqual(total.market_open, Decimal("100"))


class MarketHighMetricTests(TestCase):
    def setUp(self):
        # Open prices baseline
        make_session("USA", "YM", 2, last_price=Decimal("100"), market_open=Decimal("100"))
        make_session("USA", "ES", 2, last_price=Decimal("200"), market_open=Decimal("200"))

    def _enriched(self, ym_last, es_last):
        return [
            {"instrument": {"symbol": "/YM"}, "last": str(ym_last)},
            {"instrument": {"symbol": "/ES"}, "last": str(es_last)},
        ]

    def test_high_initial_and_updates_and_drawdown(self):
        # First tick establishes highs
        MarketHighMetric.update_from_quotes("USA", self._enriched(101, 199))
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=2)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=2)
        self.assertEqual(ym.market_high_number, Decimal("101"))
        self.assertEqual(ym.market_high_percentage, Decimal("0"))
        self.assertEqual(es.market_high_number, Decimal("199"))
        self.assertEqual(es.market_high_percentage, Decimal("0"))

        # New high for YM resets pct, ES drawdown grows
        MarketHighMetric.update_from_quotes("USA", self._enriched(103, 198))
        ym.refresh_from_db(); es.refresh_from_db()
        self.assertEqual(ym.market_high_number, Decimal("103"))
        self.assertEqual(ym.market_high_percentage, Decimal("0"))
        # Drawdown for ES: (199-198)/199*100 ≈ 0.5025
        self.assertTrue(es.market_high_percentage > Decimal("0"))

        # Below high for YM computes drawdown
        MarketHighMetric.update_from_quotes("USA", self._enriched(102, 197))
        ym.refresh_from_db()
        self.assertEqual(ym.market_high_number, Decimal("103"))  # unchanged
        self.assertTrue(ym.market_high_percentage > Decimal("0"))

    def test_high_metric_updates_total_composite(self):
        """TOTAL rows track highs separately from individual futures."""
        make_session("USA", "TOTAL", 3, last_price=Decimal("150"), market_open=Decimal("150"))
        enriched = [{"instrument": {"symbol": "/TOTAL"}, "last": "155"}]
        MarketHighMetric.update_from_quotes("USA", enriched)
        total = MarketSession.objects.get(country="USA", future="TOTAL", session_number=3)
        self.assertEqual(total.market_high_number, Decimal("155"))
        self.assertEqual(total.market_high_percentage, Decimal("0"))


class MarketLowMetricTests(TestCase):
    def setUp(self):
        make_session("USA", "YM", 3, last_price=Decimal("100"), market_open=Decimal("100"))
        make_session("USA", "ES", 3, last_price=Decimal("200"), market_open=Decimal("200"))

    def _enriched(self, ym_last, es_last):
        return [
            {"instrument": {"symbol": "/YM"}, "last": str(ym_last)},
            {"instrument": {"symbol": "/ES"}, "last": str(es_last)},
        ]

    def test_low_initial_and_run_up(self):
        # First tick establishes low
        MarketLowMetric.update_from_quotes("USA", self._enriched(99, 198))
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=3)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=3)
        self.assertEqual(ym.market_low_number, Decimal("99"))
        self.assertEqual(ym.market_low_percentage, Decimal("0"))
        self.assertEqual(es.market_low_number, Decimal("198"))
        self.assertEqual(es.market_low_percentage, Decimal("0"))

        # Run-up from low (price moves above low)
        MarketLowMetric.update_from_quotes("USA", self._enriched(100, 199))
        ym.refresh_from_db(); es.refresh_from_db()
        self.assertEqual(ym.market_low_number, Decimal("99"))
        self.assertTrue(ym.market_low_percentage > Decimal("0"))
        self.assertEqual(es.market_low_number, Decimal("198"))
        self.assertTrue(es.market_low_percentage > Decimal("0"))

        # New lower low resets percentage
        MarketLowMetric.update_from_quotes("USA", self._enriched(98, 197))
        ym.refresh_from_db(); es.refresh_from_db()
        self.assertEqual(ym.market_low_number, Decimal("98"))
        self.assertEqual(ym.market_low_percentage, Decimal("0"))
        self.assertEqual(es.market_low_number, Decimal("197"))
        self.assertEqual(es.market_low_percentage, Decimal("0"))

    def test_low_metric_updates_total_composite(self):
        """TOTAL rows track lows separately from individual futures."""
        make_session("USA", "TOTAL", 4, last_price=Decimal("150"), market_open=Decimal("150"))
        enriched = [{"instrument": {"symbol": "/TOTAL"}, "last": "145"}]
        MarketLowMetric.update_from_quotes("USA", enriched)
        total = MarketSession.objects.get(country="USA", future="TOTAL", session_number=4)
        self.assertEqual(total.market_low_number, Decimal("145"))
        self.assertEqual(total.market_low_percentage, Decimal("0"))
        # Price moves above low
        enriched = [{"instrument": {"symbol": "/TOTAL"}, "last": "148"}]
        MarketLowMetric.update_from_quotes("USA", enriched)
        total.refresh_from_db()
        self.assertTrue(total.market_low_percentage > Decimal("0"))


class MarketCloseAndRangeMetricTests(TestCase):
    def setUp(self):
        # Prepare session 4 with highs/lows
        make_session("USA", "YM", 4, last_price=Decimal("105"), market_open=Decimal("100"), high=Decimal("105"), low=Decimal("99"))
        make_session("USA", "ES", 4, last_price=Decimal("210"), market_open=Decimal("200"), high=Decimal("212"), low=Decimal("198"))

    def _enriched(self, ym_last, es_last):
        return [
            {"instrument": {"symbol": "/YM"}, "last": str(ym_last)},
            {"instrument": {"symbol": "/ES"}, "last": str(es_last)},
        ]

    def test_close_metric(self):
        MarketCloseMetric.update_for_country_on_close("USA", self._enriched(106, 211))
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=4)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=4)
        self.assertEqual(ym.market_close_number, Decimal("106"))
        self.assertEqual(es.market_close_number, Decimal("211"))
        # Percentage move from open
        self.assertEqual(ym.market_close_percentage, Decimal("6"))  # (106-100)/100*100
        self.assertEqual(es.market_close_percentage, Decimal("5.5"))  # (211-200)/200*100

    def test_range_metric(self):
        # First run close metric so highs/lows considered final
        MarketCloseMetric.update_for_country_on_close("USA", self._enriched(106, 211))
        MarketRangeMetric.update_for_country_on_close("USA")
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=4)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=4)
        self.assertEqual(ym.market_range_number, Decimal("105") - Decimal("99"))
        self.assertEqual(es.market_range_number, Decimal("212") - Decimal("198"))
        # Range percentage = range / open * 100
        self.assertEqual(ym.market_range_percentage, (Decimal("105") - Decimal("99")) / Decimal("100") * Decimal("100"))
        self.assertEqual(es.market_range_percentage, (Decimal("212") - Decimal("198")) / Decimal("200") * Decimal("100"))

    def test_close_and_range_for_total_composite(self):
        """TOTAL rows get close and range metrics computed."""
        make_session("USA", "TOTAL", 5, last_price=Decimal("150"), market_open=Decimal("150"), high=Decimal("160"), low=Decimal("145"))
        enriched = [{"instrument": {"symbol": "/TOTAL"}, "last": "155"}]
        MarketCloseMetric.update_for_country_on_close("USA", enriched)
        MarketRangeMetric.update_for_country_on_close("USA")
        total = MarketSession.objects.get(country="USA", future="TOTAL", session_number=5)
        self.assertEqual(total.market_close_number, Decimal("155"))
        # (155-150)/150*100 = 3.333...
        self.assertTrue(Decimal("3.33") < total.market_close_percentage < Decimal("3.34"))
        self.assertEqual(total.market_range_number, Decimal("15"))  # 160-145
        self.assertEqual(total.market_range_percentage, Decimal("10"))  # 15/150*100


class MarketMetricEdgeCaseTests(TestCase):
    """Edge-case coverage for metrics (missing data, zero baselines, empty quotes)."""

    def test_high_metric_skips_when_open_missing_or_zero(self):
        # Session with market_open None
        make_session("USA", "YM", 5, last_price=Decimal("100"), market_open=None)
        # Session with market_open zero
        make_session("USA", "ES", 5, last_price=Decimal("200"), market_open=Decimal("0"))

        enriched = [
            {"instrument": {"symbol": "/YM"}, "last": "101"},
            {"instrument": {"symbol": "/ES"}, "last": "201"},
        ]
        updated = MarketHighMetric.update_from_quotes("USA", enriched)
        self.assertEqual(updated, 0, "Should skip updates when open is None or 0")
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=5)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=5)
        self.assertIsNone(ym.market_high_number)
        self.assertIsNone(es.market_high_number)

    def test_low_metric_skips_when_no_quotes(self):
        make_session("USA", "YM", 6, last_price=Decimal("100"), market_open=Decimal("100"))
        updated = MarketLowMetric.update_from_quotes("USA", [])
        self.assertEqual(updated, 0)
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=6)
        self.assertIsNone(ym.market_low_number)

    def test_close_metric_percentage_none_when_open_missing_or_zero(self):
        make_session("USA", "YM", 7, last_price=Decimal("150"), market_open=None)
        make_session("USA", "ES", 7, last_price=Decimal("250"), market_open=Decimal("0"))
        enriched = [
            {"instrument": {"symbol": "/YM"}, "last": "151"},
            {"instrument": {"symbol": "/ES"}, "last": "251"},
        ]
        MarketCloseMetric.update_for_country_on_close("USA", enriched)
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=7)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=7)
        self.assertEqual(ym.market_close_number, Decimal("151"))
        self.assertEqual(es.market_close_number, Decimal("251"))
        self.assertIsNone(ym.market_close_percentage)
        self.assertIsNone(es.market_close_percentage)

    def test_range_metric_skips_when_missing_high_or_low(self):
        # Missing low
        make_session("USA", "YM", 8, market_open=Decimal("100"), high=Decimal("110"), low=None)
        # Missing high
        make_session("USA", "ES", 8, market_open=Decimal("200"), high=None, low=Decimal("195"))
        # Complete values for control
        make_session("USA", "NQ", 8, market_open=Decimal("300"), high=Decimal("315"), low=Decimal("290"))
        updated = MarketRangeMetric.update_for_country_on_close("USA")
        # Only NQ should update
        self.assertEqual(updated, 1)
        nq = MarketSession.objects.get(country="USA", future="NQ", session_number=8)
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=8)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=8)
        self.assertEqual(nq.market_range_number, Decimal("315") - Decimal("290"))
        self.assertIsNone(ym.market_range_number)
        self.assertIsNone(es.market_range_number)

    def test_range_metric_percentage_none_when_open_zero(self):
        make_session("USA", "YM", 9, market_open=Decimal("0"), high=Decimal("110"), low=Decimal("100"))
        updated = MarketRangeMetric.update_for_country_on_close("USA")
        self.assertEqual(updated, 1)
        ym = MarketSession.objects.get(country="USA", future="YM", session_number=9)
        self.assertEqual(ym.market_range_number, Decimal("10"))
        self.assertIsNone(ym.market_range_percentage)
