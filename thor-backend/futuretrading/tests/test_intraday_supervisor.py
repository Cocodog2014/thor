import time
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase

from FutureTrading.models.MarketSession import MarketSession
from FutureTrading.services.IntradayMarketSupervisor import IntradayMarketSupervisor


class DummyMarket:
    def __init__(self, market_id: int, country: str):
        self.id = market_id
        self.country = country


def make_session(country: str, future: str, session_number: int, last_price, market_open):
    return MarketSession.objects.create(
        session_number=session_number,
        year=2025,
        month=11,
        date=22,
        day="Sat",
        country=country,
        future=future,
        last_price=Decimal(str(last_price)),
        market_open=Decimal(str(market_open)),
    )


class IntradayMarketSupervisorTests(TestCase):
    def setUp(self):
        make_session("USA", "YM", 100, last_price=Decimal("100"), market_open=Decimal("100"))
        make_session("USA", "ES", 100, last_price=Decimal("200"), market_open=Decimal("200"))
        make_session("USA", "TOTAL", 100, last_price=Decimal("150"), market_open=Decimal("150"))
        self.market = DummyMarket(1, "USA")

    def test_manual_metric_flow_without_threads(self):
        """Deterministic metric progression without threads for reliability."""
        from FutureTrading.services.market_metrics import (
            MarketHighMetric,
            MarketLowMetric,
            MarketCloseMetric,
            MarketRangeMetric,
        )

        ticks = [
            [
                {"instrument": {"symbol": "/YM"}, "last": "101"},
                {"instrument": {"symbol": "/ES"}, "last": "201"},
                {"instrument": {"symbol": "/TOTAL"}, "last": "151"},
            ],
            [
                {"instrument": {"symbol": "/YM"}, "last": "105"},
                {"instrument": {"symbol": "/ES"}, "last": "210"},
                {"instrument": {"symbol": "/TOTAL"}, "last": "155"},
            ],
            [
                {"instrument": {"symbol": "/YM"}, "last": "103"},
                {"instrument": {"symbol": "/ES"}, "last": "205"},
                {"instrument": {"symbol": "/TOTAL"}, "last": "153"},
            ],
        ]

        for enriched in ticks:
            MarketHighMetric.update_from_quotes("USA", enriched)
            MarketLowMetric.update_from_quotes("USA", enriched)

        ym = MarketSession.objects.get(country="USA", future="YM", session_number=100)
        es = MarketSession.objects.get(country="USA", future="ES", session_number=100)
        total = MarketSession.objects.get(country="USA", future="TOTAL", session_number=100)
        self.assertEqual(ym.market_high_open, Decimal("105"))
        self.assertEqual(es.market_high_open, Decimal("210"))
        self.assertEqual(total.market_high_open, Decimal("155"))
        self.assertTrue(ym.market_high_pct_open > 0)
        self.assertTrue(es.market_high_pct_open > 0)
        self.assertTrue(total.market_high_pct_open > 0)
        self.assertEqual(ym.market_low_open, Decimal("101"))
        self.assertEqual(es.market_low_open, Decimal("201"))
        self.assertEqual(total.market_low_open, Decimal("151"))
        self.assertTrue(ym.market_low_pct_open > 0)
        self.assertTrue(es.market_low_pct_open > 0)
        self.assertTrue(total.market_low_pct_open > 0)

        close_quotes = [
            {"instrument": {"symbol": "/YM"}, "last": "104"},
            {"instrument": {"symbol": "/ES"}, "last": "206"},
            {"instrument": {"symbol": "/TOTAL"}, "last": "154"},
        ]
        MarketCloseMetric.update_for_country_on_close("USA", close_quotes)
        MarketRangeMetric.update_for_country_on_close("USA")

        ym.refresh_from_db(); es.refresh_from_db(); total.refresh_from_db()
        self.assertEqual(ym.market_close, Decimal("104"))
        self.assertEqual(es.market_close, Decimal("206"))
        self.assertEqual(total.market_close, Decimal("154"))
        self.assertTrue(Decimal("0.9523") < ym.market_high_pct_close < Decimal("0.9525"))
        self.assertTrue(Decimal("2.9702") < ym.market_low_pct_close < Decimal("2.9704"))
        self.assertTrue(Decimal("1.9047") < es.market_high_pct_close < Decimal("1.9049"))
        self.assertTrue(Decimal("2.4875") < es.market_low_pct_close < Decimal("2.4877"))
        self.assertTrue(Decimal("0.6451") < total.market_high_pct_close < Decimal("0.6453"))
        self.assertTrue(Decimal("1.9866") < total.market_low_pct_close <= Decimal("1.9868"))
        self.assertEqual(ym.market_range, Decimal("105") - Decimal("101"))
        self.assertEqual(es.market_range, Decimal("210") - Decimal("201"))
        self.assertEqual(total.market_range, Decimal("155") - Decimal("151"))
        self.assertEqual(ym.market_range_pct, (Decimal("105") - Decimal("101")) / Decimal("100") * Decimal("100"))
        self.assertEqual(es.market_range_pct, (Decimal("210") - Decimal("201")) / Decimal("200") * Decimal("100"))
        # TOTAL range % with tolerance for rounding: (155-151)/150*100 = 2.666...
        self.assertTrue(Decimal("2.66") < total.market_range_pct < Decimal("2.67"))
