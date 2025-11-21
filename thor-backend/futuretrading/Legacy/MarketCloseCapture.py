"""
Market Close Capture Logic

Captures futures data when a global market closes and stores close-time
snapshots linked to the day's MarketOpenSession.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from FutureTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.services.classification import enrich_quote_row, compute_composite

logger = logging.getLogger(__name__)


class MarketCloseCaptureService:
    """Captures close-time futures data for the active session."""

    FUTURES_SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']

    def _get_today_session(self, country: str) -> MarketOpenSession | None:
        now = timezone.now()
        return (
            MarketOpenSession.objects
            .filter(country=country, year=now.year, month=now.month, date=now.day)
            .order_by('-captured_at')
            .first()
        )

    def _fetch_quotes(self):
        data = {}
        for sym in self.FUTURES_SYMBOLS:
            try:
                q = live_data_redis.get_latest_quote(sym)
                if q:
                    data[sym] = q
                else:
                    logger.warning(f"No Redis data for {sym} at close")
            except Exception as e:
                logger.error(f"Error fetching {sym} from Redis: {e}")
        return data

    def _enrich_rows(self, quotes: dict[str, dict]) -> list[dict]:
        rows = []
        for idx, (symbol, q) in enumerate(quotes.items()):
            def to_str(val):
                return str(val) if val is not None else None

            row = {
                'instrument': {
                    'id': idx + 1,
                    'symbol': symbol,
                    'name': symbol,
                    'exchange': 'TOS',
                    'currency': 'USD',
                    'display_precision': 2,
                    'is_active': True,
                    'sort_order': idx
                },
                'price': to_str(q.get('last')),
                'last': to_str(q.get('last')),
                'bid': to_str(q.get('bid')),
                'ask': to_str(q.get('ask')),
                'volume': q.get('volume'),
                'open_price': to_str(q.get('open')),
                'high_price': to_str(q.get('high')),
                'low_price': to_str(q.get('low')),
                'close_price': to_str(q.get('close')),
                'previous_close': to_str(q.get('close')),
                'change': to_str(q.get('change')),
                'change_percent': None,
                'vwap': None,
                'bid_size': q.get('bid_size'),
                'ask_size': q.get('ask_size'),
                'extended_data': {},
            }
            try:
                enrich_quote_row(row)
            except Exception as e:
                logger.warning(f"Enrich failed for {symbol}: {e}")
            rows.append(row)
        return rows

    @transaction.atomic
    def capture_market_close(self, market) -> MarketOpenSession | None:
        """Find today's session for the given market and capture close-time snapshots."""
        try:
            session = self._get_today_session(market.country)
            if not session:
                logger.warning(f"No open session found for {market.country} today; skipping close capture")
                return None

            quotes = self._fetch_quotes()
            if not quotes:
                logger.error(f"No quotes available for {market.country} at close")
                return session

            rows = self._enrich_rows(quotes)
            try:
                total = compute_composite(rows)
            except Exception as e:
                logger.warning(f"Composite failed at close: {e}")
                total = None

            # Upsert per-future close snapshots
            created = 0
            for sym in self.FUTURES_SYMBOLS:
                q = quotes.get(sym)
                r = next((x for x in rows if x['instrument']['symbol'] == sym), None)
                if not q:
                    continue

                payload = {
                    'last_price': _dec(q.get('last')),
                    'change': _dec(q.get('change')),
                    'change_percent': _dec((r or {}).get('change_percent')),
                    'bid': _dec(q.get('bid')),
                    'ask': _dec(q.get('ask')),
                    'bid_size': _to_int(q.get('bid_size')),
                    'ask_size': _to_int(q.get('ask_size')),
                    'volume': _to_int(q.get('volume')),
                    'vwap': _dec(q.get('vwap')),
                    'open': _dec(q.get('open')),
                    'close': _dec(q.get('close')),
                }
                if payload['bid'] is not None and payload['ask'] is not None:
                    payload['spread'] = payload['ask'] - payload['bid']

                obj, _ = FutureCloseSnapshot.objects.update_or_create(
                    session=session, symbol=sym,
                    defaults=payload,
                )
                created += 1

            # TOTAL close snapshot
            if total:
                t_payload = {
                    'weighted_average': _dec(total.get('weighted_average')),
                    'signal': (total.get('signal') or '').upper() if total.get('signal') else None,
                    'sum_weighted': _dec(total.get('sum_weighted')),
                    'instrument_count': total.get('instrument_count') or 11,
                    'status': 'CLOSE TOTAL',
                }
                # Derive weight as sum of per-row weights if available
                try:
                    t_weight = int(round(sum(int(_safe_weight(x)) for x in rows)))
                except Exception:
                    t_weight = None
                t_payload['weight'] = t_weight

                FutureCloseSnapshot.objects.update_or_create(
                    session=session, symbol='TOTAL', defaults=t_payload
                )

            logger.info(f"📘 Close capture complete for {market.country} – {created} futures + TOTAL")
            return session

        except Exception as e:
            logger.error(f"Close capture failed for {market.country}: {e}", exc_info=True)
            return None


# Helpers
def _dec(val):
    try:
        return Decimal(str(val)) if val not in (None, '') else None
    except Exception:
        return None


def _to_int(val):
    try:
        return int(val) if val not in (None, '') else None
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None


def _safe_weight(row: dict) -> int:
    w = row.get('signal_weight') if row.get('signal_weight') is not None else row.get('contract_weight')
    try:
        return int(w) if w is not None else 0
    except Exception:
        try:
            return int(float(w)) if w is not None else 0
        except Exception:
            return 0


# Singleton and public API
_close_capture = MarketCloseCaptureService()


def capture_market_close(market):
    return _close_capture.capture_market_close(market)


__all__ = ['capture_market_close', 'MarketCloseCaptureService']
