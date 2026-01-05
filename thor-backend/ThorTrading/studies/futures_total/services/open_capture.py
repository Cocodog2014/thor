from __future__ import annotations

import logging
import os
from datetime import date as date_cls
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from GlobalMarkets.models.market import Market
from GlobalMarkets.services.active_markets import get_control_markets
from GlobalMarkets.services.market_clock import is_market_open_now
from LiveData.shared.redis_client import live_data_redis
from Instruments.models import Instrument
from ThorTrading.studies.futures_total.models.market_session import MarketSession
from ThorTrading.studies.futures_total.services.analytics.backtest_stats import compute_backtest_stats_for_country_symbol
from GlobalMarkets.services.normalize import normalize_country_code
from ThorTrading.studies.futures_total.services.indicators import compute_targets_for_symbol
from ThorTrading.studies.futures_total.services.sessions.analytics.wndw_totals import CountrySymbolWndwTotalsService
from ThorTrading.studies.futures_total.services.sessions.counters import CountrySymbolCounter
from ThorTrading.studies.futures_total.services.sessions.metrics import MarketOpenMetric
from ThorTrading.studies.futures_total.quotes import get_enriched_quotes_with_composite

logger = logging.getLogger(__name__)

# Only allow fields that exist on MarketSession to avoid runtime errors
ALLOWED_SESSION_FIELDS = {
    "session_number",
    "capture_kind",
    "year",
    "month",
    "date",
    "day",
    "country",
    "symbol",
    "captured_at",
    "last_price",
    "ask_price",
    "ask_size",
    "bid_price",
    "bid_size",
    "volume",
    "spread",
    "open_price_24h",
    "prev_close_24h",
    "open_prev_diff_24h",
    "open_prev_pct_24h",
    "low_24h",
    "high_24h",
    "range_diff_24h",
    "range_pct_24h",
    "low_52w",
    "low_pct_52w",
    "high_52w",
    "high_pct_52w",
    "range_52w",
    "range_pct_52w",
    "bhs",
    "weight",
    "entry_price",
    "target_high",
    "target_low",
    "weighted_average",
    "instrument_count",
    "change",
    "change_percent",
    "market_open",
    "market_high_open",
    "market_high_pct_open",
    "market_low_open",
    "market_low_pct_open",
    "market_close",
    "market_high_pct_close",
    "market_low_pct_close",
    "market_close_vs_open_pct",
    "market_range",
    "market_range_pct",
    "session_volume",
    "country_symbol",
    "country_symbol_wndw_total",
    "target_hit_price",
    "target_hit_type",
    "target_hit_at",
    "strong_buy_worked",
    "strong_buy_worked_percentage",
    "strong_buy_didnt_work",
    "strong_buy_didnt_work_percentage",
    "buy_worked",
    "buy_worked_percentage",
    "buy_didnt_work",
    "buy_didnt_work_percentage",
    "hold",
    "strong_sell_worked",
    "strong_sell_worked_percentage",
    "strong_sell_didnt_work",
    "strong_sell_didnt_work_percentage",
    "sell_worked",
    "sell_worked_percentage",
    "sell_didnt_work",
    "sell_didnt_work_percentage",
}


class MarketOpenCaptureService:
    """Captures symbol data at market open - matches RTD endpoint logic."""

    def get_next_session_number(self) -> int:
        last = MarketSession.objects.order_by("-session_number").first()
        return (last.session_number + 1) if last else 1

    def safe_decimal(self, val):
        if val is None:
            return None
        try:
            if isinstance(val, Decimal):
                return val
            return Decimal(str(val))
        except Exception:
            return None

    def _get_or_create_session(self, *, lookup: dict, defaults: dict):
        try:
            with transaction.atomic():
                obj, created = MarketSession.objects.get_or_create(**lookup, defaults=defaults)
                return obj, created
        except IntegrityError:
            # likely unique constraint collision
            try:
                return MarketSession.objects.get(**lookup), False
            except MarketSession.DoesNotExist:
                raise

    def _open_session_exists(self, session_number: int) -> bool:
        return MarketSession.objects.filter(session_number=session_number, capture_kind="OPEN").exists()

    def _market_open_capture_exists_for_date(self, country: str | None, market_date: date_cls) -> bool:
        if not country:
            return False
        return MarketSession.objects.filter(
            country=country,
            capture_kind="OPEN",
            year=market_date.year,
            month=market_date.month,
            date=market_date.day,
        ).exists()

    def _allowed_symbols_for_country(self, country: str | None) -> tuple[set[str], bool]:
        """Return (allowed_symbols, used_fallback).

        allowed_symbols derived from the canonical Instruments catalog; if empty, use a fallback set.
        """
        if not country:
            return set(), False

        qs = Instrument.objects.filter(is_active=True)
        if country:
            qs = qs.filter(country__iexact=country)

        symbols: set[str] = set()
        for inst in qs.only("symbol"):
            sym = getattr(inst, "symbol", None)
            if sym:
                symbols.add(str(sym).lstrip("/").upper())

        if symbols:
            return symbols, False

        # Fallback list (existing behavior): if no instruments configured for the country,
        # we will capture whatever enriched quotes provide.
        return set(), False

    def create_session_for_symbol(
        self,
        symbol: str,
        row: dict,
        session_number: int,
        time_info: dict,
        country: str | None,
        composite_signal: str,
    ):
        # This logic is the canonical open-capture implementation.
        data = {
            "session_number": session_number,
            "capture_kind": "OPEN",
            "year": time_info.get("year"),
            "month": time_info.get("month"),
            "date": time_info.get("date"),
            "day": time_info.get("day"),
            "country": country,
            "symbol": symbol,
            "captured_at": timezone.now(),
        }

        # Price fields
        data["last_price"] = self.safe_decimal(row.get("last") or row.get("price"))
        data["ask_price"] = self.safe_decimal(row.get("ask"))
        data["bid_price"] = self.safe_decimal(row.get("bid"))
        data["ask_size"] = row.get("ask_size")
        data["bid_size"] = row.get("bid_size")
        data["volume"] = row.get("volume")

        # Derived metrics (already computed on row)
        data["spread"] = self.safe_decimal(row.get("spread"))
        data["change"] = self.safe_decimal(row.get("change"))
        data["change_percent"] = self.safe_decimal(row.get("change_percent"))

        # 52w (from extended_data)
        ext = row.get("extended_data") or {}
        data["high_52w"] = self.safe_decimal(ext.get("high_52w"))
        data["low_52w"] = self.safe_decimal(ext.get("low_52w"))

        # Capture open snapshot stats
        data["market_open"] = data.get("last_price")
        data["market_high_open"] = data.get("last_price")
        data["market_low_open"] = data.get("last_price")
        data["market_high_pct_open"] = Decimal("0") if data.get("last_price") is not None else None
        data["market_low_pct_open"] = Decimal("0") if data.get("last_price") is not None else None

        # Symbol/key
        data["country_symbol"] = f"{country}:{symbol}" if country else symbol

        filtered = {k: v for k, v in data.items() if k in ALLOWED_SESSION_FIELDS}
        lookup = {
            "session_number": filtered.get("session_number"),
            "capture_kind": "OPEN",
            "country": filtered.get("country"),
            "symbol": filtered.get("symbol"),
        }
        defaults = {k: v for k, v in filtered.items() if k not in lookup}

        try:
            session, created = self._get_or_create_session(lookup=lookup, defaults=defaults)
        except Exception as exc:  # noqa: BLE001
            logger.error("Session creation failed for %s: %s", symbol, exc, exc_info=True)
            return None, False

        if session:
            _country_symbol_counter.assign_sequence(session)

        return session, created

    def create_session_for_total(
        self,
        composite: dict,
        session_number: int,
        time_info: dict,
        country: str | None,
        ym_entry_price=None,
    ):
        data = {
            "session_number": session_number,
            "capture_kind": "OPEN",
            "year": time_info.get("year"),
            "month": time_info.get("month"),
            "date": time_info.get("date"),
            "day": time_info.get("day"),
            "country": country,
            "symbol": "TOTAL",
            "captured_at": timezone.now(),
        }

        composite_signal = (composite.get("composite_signal") or composite.get("signal") or "HOLD").upper()
        weighted_average = composite.get("weighted_average") or composite.get("score")
        data["weighted_average"] = self.safe_decimal(weighted_average)
        try:
            data["instrument_count"] = int(
                composite.get("instrument_count") or len(composite.get("contributions") or {})
            )
        except Exception:
            data["instrument_count"] = None

        if ym_entry_price is not None:
            data["entry_price"] = ym_entry_price
            high, low = compute_targets_for_symbol(country, "YM", ym_entry_price)
            data["target_high"] = high
            data["target_low"] = low

        try:
            stats = compute_backtest_stats_for_country_symbol(
                country=country,
                symbol="TOTAL",
                as_of=data["captured_at"],
            )
            data.update(stats)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backtest stats failed for TOTAL: %s", exc)

        filtered = {k: v for k, v in data.items() if k in ALLOWED_SESSION_FIELDS}
        lookup = {
            "session_number": filtered.get("session_number"),
            "capture_kind": "OPEN",
            "symbol": filtered.get("symbol"),
        }
        defaults = {k: v for k, v in filtered.items() if k not in lookup}

        try:
            session, created = self._get_or_create_session(lookup=lookup, defaults=defaults)
        except Exception as exc:  # noqa: BLE001
            logger.error("TOTAL session creation failed: %s", exc, exc_info=True)
            return None, False

        if session:
            _country_symbol_counter.assign_sequence(session)
            if data.get("weighted_average"):
                logger.info("TOTAL session: %.4f -> %s", float(data["weighted_average"]), composite_signal)
            else:
                logger.info("TOTAL: %s", composite_signal)

        return session, created

    def capture_market_open(self, market: Market, *, session_number: int | None = None):
        from ThorTrading.studies.futures_total.services.global_market_gate import (
            open_capture_allowed,
            session_tracking_allowed,
        )

        display_country = getattr(market, "country", None)
        country_code = normalize_country_code(display_country) or display_country

        if not session_tracking_allowed(market):
            logger.info("Session capture disabled for %s; skipping.", country_code or display_country or "?")
            return None
        if not open_capture_allowed(market):
            logger.info("Open capture disabled for %s; skipping.", country_code or display_country or "?")
            return None

        try:
            if session_number is None:
                session_number = live_data_redis.get_active_session_number()

            # For stability, do not mint new session numbers here.
            if session_number is None:
                logger.debug(
                    "Open capture skipped for %s: missing active session_number",
                    country_code or display_country or "?",
                )
                return None

            # Idempotence: once per session_number.
            if self._open_session_exists(int(session_number)):
                return None

            logger.info("Capturing %s market open...", country_code or display_country or "?")

            allowed_symbols, used_fallback = self._allowed_symbols_for_country(country_code or display_country)
            logger.info(
                "OpenCapture %s: allowed_symbols=%d",
                country_code or display_country,
                len(allowed_symbols),
            )
            if used_fallback:
                logger.warning(
                    "No instruments configured for %s; fallback instruments were persisted to country",
                    country_code or display_country,
                )

            enriched, composite = get_enriched_quotes_with_composite()
            if not enriched:
                logger.error("No enriched rows for %s", country_code or display_country or "?")
                return None

            filtered = []
            missing_country = []
            market_code = country_code or display_country

            for r in enriched:
                symbol = (r.get("instrument", {}) or {}).get("symbol") or ""
                base_symbol = symbol.lstrip("/").upper()
                if not base_symbol:
                    continue

                # Gate by configured instruments for this market
                if allowed_symbols and base_symbol not in allowed_symbols:
                    continue

                # If the feed provides a country, enforce it.
                row_country_raw = r.get("country")
                row_country = normalize_country_code(row_country_raw) if row_country_raw else None
                if row_country and row_country != market_code:
                    continue

                # If country missing, allow it (it already passed allowed_symbols)
                if not row_country:
                    missing_country.append(base_symbol)

                filtered.append(r)

            enriched = filtered
            logger.info(
                "OpenCapture %s: enriched_rows=%d after filtering (missing_country=%d)",
                market_code,
                len(enriched),
                len(missing_country),
            )

            if not enriched:
                logger.error(
                    "No enriched rows for %s after symbol filter (missing_country=%d)",
                    country_code or display_country or "?",
                    len(missing_country),
                )
                return None

            composite_signal = (composite.get("composite_signal") or composite.get("signal") or "HOLD").upper()
            time_info = _market_time_info(market)

            session_number = int(session_number)

            sessions_created = []
            skipped = []
            failures = []
            created_count = 0
            ym_entry_price = None

            for row in enriched:
                symbol = row.get("instrument", {}).get("symbol")
                if not symbol:
                    continue

                base_symbol = symbol.lstrip("/").upper()

                session, created = self.create_session_for_symbol(
                    symbol,
                    row,
                    session_number,
                    time_info,
                    country_code or display_country,
                    composite_signal,
                )

                if session:
                    sessions_created.append(session)
                    if created:
                        created_count += 1
                    else:
                        skipped.append(base_symbol)
                else:
                    failures.append(base_symbol)

                if base_symbol == "YM" and composite_signal not in ["HOLD", ""]:
                    if composite_signal in ["BUY", "STRONG_BUY"]:
                        ym_entry_price = self.safe_decimal(row.get("ask"))
                    elif composite_signal in ["SELL", "STRONG_SELL"]:
                        ym_entry_price = self.safe_decimal(row.get("bid"))

            total_session, total_created = self.create_session_for_total(
                composite,
                session_number,
                time_info,
                country_code or display_country,
                ym_entry_price=ym_entry_price,
            )
            if total_session:
                sessions_created.append(total_session)
                if total_created:
                    created_count += 1
                else:
                    skipped.append("TOTAL")

            try:
                MarketOpenMetric.update_for_session_group(session_number)
            except Exception as metrics_error:  # noqa: BLE001
                logger.warning(
                    "market_open refresh failed for session %s: %s",
                    session_number,
                    metrics_error,
                    exc_info=True,
                )

            try:
                _country_symbol_wndw_service.update_for_session_group(
                    session_group=session_number,
                    country=country_code or display_country,
                )
            except Exception as stats_error:  # noqa: BLE001
                logger.warning(
                    "Failed country/symbol WNDW totals refresh after capture %s: %s",
                    session_number,
                    stats_error,
                    exc_info=True,
                )

            logger.info(
                "Capture complete: %s Session #%s, created=%s, skipped=%s%s",
                country_code or display_country or "?",
                session_number,
                created_count,
                len(skipped),
                (f", failures={failures}" if failures else ""),
            )
            return sessions_created[0] if sessions_created else None

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Capture failed for %s: %s",
                country_code or display_country or "?",
                exc,
                exc_info=True,
            )
            return None


_service = MarketOpenCaptureService()

# Renamed variables (instrument-neutral)
_country_symbol_counter = CountrySymbolCounter()
_country_symbol_wndw_service = CountrySymbolWndwTotalsService()


def _get_capture_interval() -> float:
    setting = getattr(settings, "THORTRADING_MARKET_OPEN_CAPTURE_INTERVAL", None)
    if setting is None:
        setting = getattr(settings, "TRADING_MARKET_OPEN_CAPTURE_INTERVAL", None)

    if setting is not None:
        try:
            return max(1.0, float(setting))
        except (TypeError, ValueError):
            logger.warning("Invalid market open capture interval setting %r", setting)

    env = os.getenv("THORTRADING_MARKET_OPEN_CAPTURE_INTERVAL") or os.getenv("TRADING_MARKET_OPEN_CAPTURE_INTERVAL")
    if env:
        try:
            return max(1.0, float(env))
        except (TypeError, ValueError):
            logger.warning("Invalid market open capture interval env %r", env)

    return 1.0


def _market_timezone(market: Market) -> ZoneInfo:
    tz_name = getattr(market, "timezone_name", None) or getattr(market, "timezone", None)
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning(
                "Unknown timezone %s for %s; using default timezone instead",
                tz_name,
                getattr(market, "country", "?"),
            )

    try:
        default_tz = timezone.get_default_timezone()
        key = getattr(default_tz, "key", None) or getattr(default_tz, "zone", None) or str(default_tz)
        return ZoneInfo(key)
    except Exception:
        return timezone.utc


def _market_time_info(market: Market) -> dict:
    market_now = timezone.now().astimezone(_market_timezone(market))
    return {
        "year": market_now.year,
        "month": market_now.month,
        "date": market_now.day,
        "day": market_now.strftime("%a"),
        "date_obj": market_now.date(),
    }


def _market_local_date(market: Market) -> date_cls:
    try:
        return _market_time_info(market)["date_obj"]
    except Exception:
        return timezone.now().date()


def _scan_and_capture_once() -> int:
    """Scan all control markets and capture OPEN for any market that is OPEN now.

    Capture will only run once per active session_number.
    """
    captures = 0

    markets = list(get_control_markets())
    if not markets:
        return 0

    session_number = None
    try:
        session_number = live_data_redis.get_active_session_number()
    except Exception:
        session_number = None

    if session_number is None:
        return 0

    session_number = int(session_number)
    if MarketSession.objects.filter(session_number=session_number, capture_kind="OPEN").exists():
        return 0

    for market in markets:
        country_code = getattr(market, "country", None)
        if not country_code:
            continue

        try:
            if not is_market_open_now(market):
                continue
        except Exception:
            logger.exception("OpenCapture scan: failed open check for %s", country_code)
            continue

        try:
            result = capture_market_open(market, session_number=session_number)
            if result is not None:
                logger.info("OpenCapture scan: captured %s => %s", country_code, result)
                captures += 1
        except Exception:
            logger.exception("OpenCapture scan: capture failed for %s", country_code)

    return captures


def check_for_market_opens_and_capture() -> float:
    """Execute one capture scan and return the sleep interval."""
    interval = _get_capture_interval()
    if not getattr(check_for_market_opens_and_capture, "_logged_start", False):
        logger.info("🌎 Market Open Capture loop ready (interval=%.1fs)", interval)
        check_for_market_opens_and_capture._logged_start = True

    _scan_and_capture_once()
    return interval


def capture_market_open(market: Market, *, session_number: int | None = None):
    """Main entry point for market open capture (Futures Total study)."""
    return _service.capture_market_open(market, session_number=session_number)


__all__ = [
    "ALLOWED_SESSION_FIELDS",
    "MarketOpenCaptureService",
    "check_for_market_opens_and_capture",
    "capture_market_open",
    "_market_local_date",
]
