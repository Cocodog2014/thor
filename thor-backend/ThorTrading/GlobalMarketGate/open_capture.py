from __future__ import annotations

import logging
import os
from datetime import date as date_cls
from zoneinfo import ZoneInfo
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.models.rtd import TradingInstrument  # <-- adjust import if your path differs
from ThorTrading.services.analytics.backtest_stats import compute_backtest_stats_for_country_symbol
from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.services.indicators import compute_targets_for_symbol
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.sessions.analytics.wndw_totals import CountrySymbolWndwTotalsService
from ThorTrading.services.sessions.counters import CountrySymbolCounter
from ThorTrading.GlobalMarketGate.global_market_gate import (
    open_capture_allowed,
    session_tracking_allowed,
)
from GlobalMarkets.services.market_clock import is_market_open_now
from ThorTrading.services.sessions.metrics import MarketOpenMetric

logger = logging.getLogger(__name__)


# Only allow fields that exist on MarketSession to avoid runtime errors
ALLOWED_SESSION_FIELDS = {
    "session_number",
    "capture_group",
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
    "vwap",
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

    def get_next_session_number(self):
        last = MarketSession.objects.order_by("-session_number").first()
        return (last.session_number + 1) if last else 1

    def safe_decimal(self, val):
        if val in (None, "", ""):
            return None
        try:
            return Decimal(str(val))
        except Exception:  # noqa: BLE001
            return None

    def safe_int(self, val):
        if val in (None, "", ""):
            return None
        try:
            return int(val)
        except Exception:  # noqa: BLE001
            try:
                return int(float(val))
            except Exception:  # noqa: BLE001
                return None

    def _persist_fallback_instruments(self, canonical_country: str, fallback_qs):
        """Clone fallback instruments into the target country so future runs are country-scoped."""
        created_symbols = []
        with transaction.atomic():
            for inst in fallback_qs:
                defaults = {
                    "name": inst.name,
                    "description": inst.description,
                    "category": inst.category,
                    "exchange": inst.exchange,
                    "currency": inst.currency,
                    "is_active": inst.is_active,
                    "is_watchlist": inst.is_watchlist,
                    "show_in_ribbon": getattr(inst, "show_in_ribbon", False),
                    "sort_order": inst.sort_order,
                    "display_precision": inst.display_precision,
                    "tick_size": inst.tick_size,
                    "contract_size": inst.contract_size,
                    "api_provider": inst.api_provider,
                    "api_symbol": inst.api_symbol,
                    "feed_symbol": inst.feed_symbol,
                    "update_frequency": inst.update_frequency,
                    "is_market_open": False,
                    "margin_requirement": getattr(inst, "margin_requirement", None),
                    "tick_value": getattr(inst, "tick_value", None),
                }

                obj, created = TradingInstrument.objects.get_or_create(
                    country=canonical_country,
                    symbol=inst.symbol,
                    defaults=defaults,
                )
                if created:
                    created_symbols.append(obj.symbol.strip().upper())

        if created_symbols:
            logger.warning(
                "Persisted %s fallback instruments into %s: %s",
                len(created_symbols),
                canonical_country,
                created_symbols,
            )

    def _allowed_symbols_for_country(self, country_code: str) -> tuple[set[str], bool]:
        """
        Instrument-neutral allowed list from admin-managed TradingInstrument rows.

        Order of truth:
        1) Country-scoped instruments (is_active + is_watchlist)
        2) If none exist, fall back to all active+watchlist instruments (global list),
           then persist that set into the country so future runs stay country-specific.
        """

        canonical_country = normalize_country_code(country_code) or country_code

        qs = TradingInstrument.objects.filter(
            is_active=True,
            is_watchlist=True,
            country=canonical_country,
        ).values_list("symbol", flat=True)

        symbols = {s.strip().upper() for s in qs if s}
        used_fallback = False

        if not symbols:
            fallback_qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
            symbols = {s.symbol.strip().upper() for s in fallback_qs if s.symbol}
            used_fallback = True

            if symbols:
                logger.warning(
                    "No instruments configured for %s; falling back to global Trading Instruments (%s symbols) and persisting to country",
                    canonical_country,
                    len(symbols),
                )
                self._persist_fallback_instruments(canonical_country, fallback_qs)

                # Re-read the country-scoped symbols after persistence to keep captures country-specific going forward
                symbols = {
                    s.strip().upper()
                    for s in TradingInstrument.objects.filter(
                        is_active=True,
                        is_watchlist=True,
                        country=canonical_country,
                    ).values_list("symbol", flat=True)
                    if s
                }
            else:
                logger.error(
                    "No Trading Instruments available for %s; capture will be skipped",
                    canonical_country,
                )

        return symbols, used_fallback

    def create_session_for_symbol(
        self,
        symbol: str,
        row: dict,
        session_number: int,
        capture_group: int,
        time_info: dict,
        country: str,
        composite_signal: str,
    ):
        """Create one MarketSession row for a single symbol."""

        canonical_symbol = symbol.lstrip("/").upper()
        ext = row.get("extended_data", {}) or {}

        data = {
            "session_number": session_number,
            "capture_group": capture_group,
            "capture_kind": "OPEN",
            "year": time_info["year"],
            "month": time_info["month"],
            "date": time_info["date"],
            "day": time_info["day"],
            "country": country,
            "symbol": canonical_symbol,
            "captured_at": timezone.now(),
            "last_price": self.safe_decimal(row.get("last")),
            "ask_price": self.safe_decimal(row.get("ask")),
            "ask_size": self.safe_int(row.get("ask_size")),
            "bid_price": self.safe_decimal(row.get("bid")),
            "bid_size": self.safe_int(row.get("bid_size")),
            "volume": self.safe_int(row.get("volume")),
            "spread": self.safe_decimal(row.get("spread")),
            "open_price_24h": self.safe_decimal(row.get("open_price")),
            "prev_close_24h": self.safe_decimal(row.get("close_price") or row.get("previous_close")),
            "open_prev_diff_24h": self.safe_decimal(row.get("open_prev_diff")),
            "open_prev_pct_24h": self.safe_decimal(row.get("open_prev_pct")),
            "low_24h": self.safe_decimal(row.get("low_price")),
            "high_24h": self.safe_decimal(row.get("high_price")),
            "range_diff_24h": self.safe_decimal(row.get("range_diff")),
            "range_pct_24h": self.safe_decimal(row.get("range_pct")),
            "low_52w": self.safe_decimal(ext.get("low_52w")),
            "low_pct_52w": self.safe_decimal(ext.get("low_pct_52w") or ext.get("low_pct_52")),
            "high_52w": self.safe_decimal(ext.get("high_52w")),
            "range_52w": self.safe_decimal(ext.get("range_52w") or ext.get("week_52_range_high_low")),
            "range_pct_52w": self.safe_decimal(ext.get("range_pct_52w") or ext.get("week_52_range_percent")),
            "high_pct_52w": self.safe_decimal(ext.get("high_pct_52w") or ext.get("high_pct_52")),
            "bhs": (ext.get("signal") or "").upper() if ext.get("signal") else "",
            "weight": self.safe_int(ext.get("signal_weight")),
        }

        data["entry_price"] = None
        data["target_high"] = None
        data["target_low"] = None

        individual_signal = data["bhs"]
        if individual_signal and individual_signal not in ["HOLD", ""]:
            if individual_signal in ["BUY", "STRONG_BUY"]:
                data["entry_price"] = data.get("ask_price")
            elif individual_signal in ["SELL", "STRONG_SELL"]:
                data["entry_price"] = data.get("bid_price")

            entry = data["entry_price"]
            if entry:
                # NEW: pass country into the target logic
                high, low = compute_targets_for_symbol(country, canonical_symbol, entry)
                data["target_high"] = high
                data["target_low"] = low

        wlow = data.get("low_52w")
        whigh = data.get("high_52w")
        last_price = data.get("last_price")

        if wlow is not None and last_price:
            try:
                data["low_pct_52w"] = ((last_price - wlow) / last_price) * Decimal("100")
            except Exception:  # noqa: BLE001
                pass

        if whigh is not None and last_price:
            try:
                data["high_pct_52w"] = ((whigh - last_price) / last_price) * Decimal("100")
            except Exception:  # noqa: BLE001
                pass

        if wlow is not None and whigh is not None:
            try:
                data["range_52w"] = whigh - wlow
                if last_price:
                    data["range_pct_52w"] = ((whigh - wlow) / last_price) * Decimal("100")
            except Exception:  # noqa: BLE001
                pass

        try:
            stats = compute_backtest_stats_for_country_symbol(
                country=country,
                symbol=canonical_symbol,
                as_of=data["captured_at"],
            )
            data.update(stats)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backtest stats failed for %s: %s", canonical_symbol, exc)

        try:
            filtered = {k: v for k, v in data.items() if k in ALLOWED_SESSION_FIELDS}
            session = MarketSession.objects.create(**filtered)
            _country_symbol_counter.assign_sequence(session)
            logger.debug("Created %s session: %s", canonical_symbol, session.last_price)
            return session
        except Exception as exc:  # noqa: BLE001
            logger.error("Session creation failed for %s: %s", canonical_symbol, exc, exc_info=True)
            return None

    def create_session_for_total(self, composite, session_number, capture_group, time_info, country, ym_entry_price=None):
        """Create one MarketSession row for TOTAL composite."""

        composite_signal = (composite.get("composite_signal") or "HOLD").upper()

        data = {
            "session_number": session_number,
            "capture_group": capture_group,
            "capture_kind": "OPEN",
            "year": time_info["year"],
            "month": time_info["month"],
            "date": time_info["date"],
            "day": time_info["day"],
            "country": country,
            "symbol": "TOTAL",
            "captured_at": timezone.now(),
            "weighted_average": self.safe_decimal(composite.get("avg_weighted")),
            "instrument_count": composite.get("count") or 11,
            "bhs": composite_signal,
            "weight": composite.get("signal_weight_sum"),
        }

        if ym_entry_price is not None and composite_signal not in ["HOLD", ""]:
            data["entry_price"] = ym_entry_price
            # NEW: country-aware targets
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

        try:
            filtered = {k: v for k, v in data.items() if k in ALLOWED_SESSION_FIELDS}
            session = MarketSession.objects.create(**filtered)
            _country_symbol_counter.assign_sequence(session)
            if data.get("weighted_average"):
                logger.info("TOTAL session: %.4f -> %s", data["weighted_average"], composite_signal)
            else:
                logger.info("TOTAL: %s", composite_signal)
            return session
        except Exception as exc:  # noqa: BLE001
            logger.error("TOTAL session creation failed: %s", exc, exc_info=True)
            return None

    @transaction.atomic
    def capture_market_open(self, market):
        display_country = getattr(market, "country", None)
        country_code = normalize_country_code(display_country) or display_country

        if not session_tracking_allowed(market):
            logger.info("Session capture disabled for %s; skipping.", country_code or display_country or "?")
            return None
        if not open_capture_allowed(market):
            logger.info("Open capture disabled for %s; skipping.", country_code or display_country or "?")
            return None

        try:
            logger.info("Capturing %s market open...", country_code or display_country or "?")

            allowed_symbols, used_fallback = self._allowed_symbols_for_country(country_code or display_country)
            logger.info(
                "OpenCapture %s: allowed_symbols=%d",
                country_code or display_country,
                len(allowed_symbols),
            )
            if used_fallback:
                logger.warning(
                    "No instruments configured for country=%s; using global symbol set and filtering to feed country=%s",
                    country_code or display_country,
                    country_code or display_country,
                )

            enriched, composite = get_enriched_quotes_with_composite()
            if not enriched:
                logger.error("No enriched rows for %s", country_code or display_country or "?")
                return None

            filtered = []
            dropped_missing_country = []
            for r in enriched:
                symbol = (r.get("instrument", {}) or {}).get("symbol") or ""
                base_symbol = symbol.lstrip("/").upper()

                if allowed_symbols and base_symbol not in allowed_symbols:
                    continue

                row_country_raw = r.get("country")
                row_country = normalize_country_code(row_country_raw) if row_country_raw else None

                # Always enforce country match to avoid cross-market borrowing, even during fallback
                if not row_country:
                    dropped_missing_country.append(base_symbol)
                    continue
                if row_country != (country_code or display_country):
                    continue

                filtered.append(r)

            enriched = filtered
            logger.info(
                "OpenCapture %s: enriched_rows=%d after filtering (dropped_missing_country=%d)",
                country_code or display_country,
                len(enriched),
                len(dropped_missing_country),
            )
            if not enriched:
                logger.error(
                    "No enriched rows for %s after country/symbol filter%s",
                    country_code or display_country or "?",
                    f"; dropped_missing_country={dropped_missing_country}" if dropped_missing_country else "",
                )
                return None

            composite_signal = (composite.get("composite_signal") or "HOLD").upper()
            time_info = _market_time_info(market)

            session_number = self.get_next_session_number()
            with transaction.atomic():
                last_group_val = (
                    MarketSession.objects.exclude(capture_group__isnull=True)
                    .aggregate(max_group=Max("capture_group"))
                    .get("max_group")
                ) or 0
                capture_group = int(last_group_val) + 1

            sessions_created = []
            failures = []
            ym_entry_price = None

            for row in enriched:
                symbol = row["instrument"]["symbol"]

                session = self.create_session_for_symbol(
                    symbol,
                    row,
                    session_number,
                    capture_group,
                    time_info,
                    country_code or display_country,
                    composite_signal,
                )
                if session:
                    sessions_created.append(session)
                else:
                    failures.append(symbol)

                base_symbol = symbol.lstrip("/").upper()
                if base_symbol == "YM" and composite_signal not in ["HOLD", ""]:
                    if composite_signal in ["BUY", "STRONG_BUY"]:
                        ym_entry_price = self.safe_decimal(row.get("ask"))
                    elif composite_signal in ["SELL", "STRONG_SELL"]:
                        ym_entry_price = self.safe_decimal(row.get("bid"))

            total_session = self.create_session_for_total(
                composite,
                session_number,
                capture_group,
                time_info,
                country_code or display_country,
                ym_entry_price=ym_entry_price,
            )
            if total_session:
                sessions_created.append(total_session)

            try:
                MarketOpenMetric.update_for_capture_group(capture_group)
            except Exception as metrics_error:  # noqa: BLE001
                logger.warning("market_open refresh failed for session %s: %s", session_number, metrics_error, exc_info=True)

            try:
                _country_symbol_wndw_service.update_for_capture_group(
                    capture_group=capture_group,
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
                "Capture complete: %s Session #%s, created=%s%s",
                country_code or display_country or "?",
                session_number,
                len(sessions_created),
                (f", failures={failures}" if failures else ""),
            )
            return sessions_created[0] if sessions_created else None

        except Exception as exc:  # noqa: BLE001
            logger.error("Capture failed for %s: %s", country_code or display_country or "?", exc, exc_info=True)
            return None


_service = MarketOpenCaptureService()

# Renamed variables (instrument-neutral)
_country_symbol_counter = CountrySymbolCounter()
_country_symbol_wndw_service = CountrySymbolWndwTotalsService()


def _get_capture_interval() -> float:
    # Prefer new setting/env name but keep backward compatibility
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


def _market_timezone(market) -> ZoneInfo:
    """Resolve the market timezone with a defensive fallback."""
    tz_name = getattr(market, "timezone_name", None) or getattr(market, "timezone", None)
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning("Unknown timezone %s for %s; using default timezone instead", tz_name, getattr(market, "country", "?"))

    try:
        default_tz = timezone.get_default_timezone()
        key = getattr(default_tz, "key", None) or getattr(default_tz, "zone", None) or str(default_tz)
        return ZoneInfo(key)
    except Exception:
        return timezone.utc


def _market_time_info(market) -> dict:
    """Build a date/time info dict using the market's local timezone."""
    market_now = timezone.now().astimezone(_market_timezone(market))
    return {
        "year": market_now.year,
        "month": market_now.month,
        "date": market_now.day,
        "day": market_now.strftime("%a"),
        "date_obj": market_now.date(),
    }


def _market_local_date(market) -> date_cls:
    try:
        return _market_time_info(market)["date_obj"]
    except Exception:
        return timezone.now().date()


def _has_capture_for_date(market, capture_date: date_cls) -> bool:
    country_code = normalize_country_code(getattr(market, "country", None)) or getattr(market, "country", None)
    latest = (
        MarketSession.objects.filter(country=country_code)
        .filter(capture_kind="OPEN")
        .exclude(capture_group__isnull=True)
        .order_by("-capture_group")
        .first()
    )
    if not latest:
        return False
    return (
        latest.year == capture_date.year
        and latest.month == capture_date.month
        and latest.date == capture_date.day
    )


def _scan_and_capture_once():
    from GlobalMarkets.models.market import Market
    markets = Market.objects.filter(is_active=True)

    for market in markets:
        if not session_tracking_allowed(market):
            continue
        if not open_capture_allowed(market):
            continue
        if not is_market_open_now(market):
            continue

        market_date = _market_local_date(market)
        try:
            already_captured = _has_capture_for_date(market, market_date)
        except Exception:
            logger.exception("Failed checking capture history for %s", market.country)
            continue

        if already_captured:
            continue

        logger.info("🌅 Market %s opened with no capture for %s — running capture", market.country, market_date)
        try:
            capture_market_open(market)
        except Exception:
            logger.exception("Market open capture failed for %s", market.country)
        else:
            logger.info("✅ Market open capture complete for %s", market.country)


def check_for_market_opens_and_capture() -> float:
    """Execute one capture scan and return the sleep interval."""
    interval = _get_capture_interval()
    if not getattr(check_for_market_opens_and_capture, "_logged_start", False):
        logger.info("🌎 Market Open Capture loop ready (interval=%.1fs)", interval)
        check_for_market_opens_and_capture._logged_start = True

    _scan_and_capture_once()
    return interval


def capture_market_open(market):
    """Main entry point for market open capture."""
    return _service.capture_market_open(market)


__all__ = [
    "capture_market_open",
    "check_for_market_opens_and_capture",
    "MarketOpenCaptureService",
]
