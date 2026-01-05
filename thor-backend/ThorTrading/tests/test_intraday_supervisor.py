from __future__ import annotations
import time
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.studies.futures_total.services.sessions.finalize_close import finalize_pending_sessions_at_close


class DummyMarket:
    def __init__(self, market_id: int, country: str):
        self.id = market_id
        self.country = country


def make_session(country: str, symbol: str, session_number: int, last_price, market_open):
    return MarketSession.objects.create(
        session_number=session_number,
        year=2025,
        month=11,
        date=22,
        day="Sat",
        country=country,
        symbol=symbol,
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
        from ThorTrading.studies.futures_total.services.sessions.metrics import (
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

        ym = MarketSession.objects.get(country="USA", symbol="YM", session_number=100)
        es = MarketSession.objects.get(country="USA", symbol="ES", session_number=100)
        total = MarketSession.objects.get(country="USA", symbol="TOTAL", session_number=100)
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

class FinalizeCloseTests(TestCase):
    def _make_session(self, *, country="USA", symbol="ES", session_number=10, wndw="PENDING", target_hit_at=None):
        return MarketSession.objects.create(
            session_number=session_number,
            year=2025,
            month=12,
            date=26,
            day="Fri",
            country=country,
            symbol=symbol,
            bhs="BUY",
            wndw=wndw,
            entry_price=Decimal("100"),
            target_high=Decimal("110"),
            target_low=Decimal("90"),
            market_open=Decimal("100"),
            last_price=Decimal("100"),
            target_hit_at=target_hit_at,
        )

    def test_finalize_uses_latest_session_number(self):
        older = self._make_session(session_number=5)
        newer = self._make_session(session_number=6)

        updated = finalize_pending_sessions_at_close("USA")

        older.refresh_from_db(); newer.refresh_from_db()
        self.assertEqual(updated, 1)
        self.assertEqual(older.wndw, "PENDING")  # untouched (not latest session)
        self.assertEqual(newer.wndw, "NEUTRAL")

    def test_finalize_skips_frozen_rows(self):
        hit_time = timezone.now()
        frozen = self._make_session(session_number=7, symbol="ES", target_hit_at=hit_time, wndw="WORKED")
        pending = self._make_session(session_number=7, symbol="NQ", target_hit_at=None, wndw="PENDING")

        updated = finalize_pending_sessions_at_close("USA", session_number=7)

        frozen.refresh_from_db(); pending.refresh_from_db()
        self.assertEqual(updated, 1)
        self.assertEqual(frozen.wndw, "WORKED")  # not touched because already frozen
        self.assertEqual(pending.wndw, "NEUTRAL")

