"""
Market Open Capture - Single-Table Design

Captures futures data at market open using the same enrichment pipeline as the live RTD endpoint.
Creates 12 MarketSession rows per market open (one per future + TOTAL).
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Max

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.constants import FUTURES_SYMBOLS
from ThorTrading.services.country_future_counts import CountryFutureCounter
from ThorTrading.services.country_future_wndw_counts import (
    CountryFutureWndwTotalsService,
)
from ThorTrading.services.market_metrics import MarketOpenMetric
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.TargetHighLow import compute_targets_for_symbol
from ThorTrading.services.backtest_stats import (
    compute_backtest_stats_for_country_future,
)
from ThorTrading.services.country_codes import normalize_country_code




logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
    """Captures futures data at market open - matches RTD endpoint logic exactly.

    Uses centralized constants from ThorTrading.constants.
    Adds capture_group for explicit grouping of rows per open event.
    """
    
    def get_next_session_number(self):
        last = MarketSession.objects.order_by('-session_number').first()
        return (last.session_number + 1) if last else 1
    
    def safe_decimal(self, val):
        if val in (None, '', ''):
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None
    
    def safe_int(self, val):
        if val in (None, '', ''):
            return None
        try:
            return int(val)
        except Exception:
            try:
                return int(float(val))
            except Exception:
                return None
    
    def create_session_for_future(self, symbol, row, session_number, capture_group, time_info, country, composite_signal):
        """Create one MarketSession row for a single future"""
        ext = row.get('extended_data', {})
        
        # Base session data
        data = {
            'session_number': session_number,
            'capture_group': capture_group,
            'year': time_info['year'],
            'month': time_info['month'],
            'date': time_info['date'],
            'day': time_info['day'],
            'country': country,
            'future': symbol,
            'captured_at': timezone.now(),
            # Removed legacy wndw/outcome framework fields
            
            # Live price data at open
            'last_price': self.safe_decimal(row.get('last')),
            'ask_price': self.safe_decimal(row.get('ask')),
            'ask_size': self.safe_int(row.get('ask_size')),
            'bid_price': self.safe_decimal(row.get('bid')),
            'bid_size': self.safe_int(row.get('bid_size')),
            'volume': self.safe_int(row.get('volume')),
            'spread': self.safe_decimal(row.get('spread')),
            
            # 24h price data (renamed)
            'open_price_24h': self.safe_decimal(row.get('open_price')),
            'prev_close_24h': self.safe_decimal(row.get('close_price') or row.get('previous_close')),
            'open_prev_diff_24h': self.safe_decimal(row.get('open_prev_diff')),
            'open_prev_pct_24h': self.safe_decimal(row.get('open_prev_pct')),
            
            # Range data
            'low_24h': self.safe_decimal(row.get('low_price')),
            'high_24h': self.safe_decimal(row.get('high_price')),
            'range_diff_24h': self.safe_decimal(row.get('range_diff')),
            'range_pct_24h': self.safe_decimal(row.get('range_pct')),
            'low_52w': self.safe_decimal(ext.get('low_52w')),
            'low_pct_52w': self.safe_decimal(ext.get('low_pct_52w') or ext.get('low_pct_52')),
            'high_52w': self.safe_decimal(ext.get('high_52w')),
            'range_52w': self.safe_decimal(ext.get('range_52w') or ext.get('week_52_range_high_low')),
            'range_pct_52w': self.safe_decimal(ext.get('range_pct_52w') or ext.get('week_52_range_percent')),
            'high_pct_52w': self.safe_decimal(ext.get('high_pct_52w') or ext.get('high_pct_52')),
            
            # Signal (individual future's signal from HBS)
            'bhs': (ext.get('signal') or '').upper() if ext.get('signal') else '',
            'weight': self.safe_int(ext.get('signal_weight')),
            # Removed legacy study_fw field (framework identifier no longer stored)
        }
        
        # Default values when there is no trade signal
        data['entry_price'] = None
        data['target_high'] = None
        data['target_low'] = None

        # Determine entry price based on INDIVIDUAL future's signal (not composite), then compute targets centrally
        individual_signal = data['bhs']
        if individual_signal and individual_signal not in ['HOLD', '']:
            if individual_signal in ['BUY', 'STRONG_BUY']:
                data['entry_price'] = data.get('ask_price')
            elif individual_signal in ['SELL', 'STRONG_SELL']:
                data['entry_price'] = data.get('bid_price')
            entry = data['entry_price']
            if entry:
                high, low = compute_targets_for_symbol(symbol, entry)
                data['target_high'] = high
                data['target_low'] = low

        # Populate 52-week range derivative fields if both ends available
        wlow = data.get('low_52w')
        whigh = data.get('high_52w')
        last_price = data.get('last_price')
        if wlow is not None:
            try:
                if last_price:
                    # Percent distance from current price down to the 52w low
                    data['low_pct_52w'] = ((last_price - wlow) / last_price) * Decimal('100')
            except Exception:
                pass

        if whigh is not None:
            try:
                if last_price:
                    data['high_pct_52w'] = ((whigh - last_price) / last_price) * Decimal('100')
            except Exception:
                pass

        if wlow is not None and whigh is not None:
            try:
                data['range_52w'] = (whigh - wlow)
                if last_price:
                    # Percent of current price occupied by 52w range
                    data['range_pct_52w'] = ((whigh - wlow) / last_price) * Decimal('100')
            except Exception:
                # Leave unset on any arithmetic issues
                pass
        
        # ---------- Backtest stats: use existing service ----------
        try:
            stats = compute_backtest_stats_for_country_future(
                country=country,
                future=symbol,
                as_of=data['captured_at'],
            )
            data.update(stats)
        except Exception as e:
            logger.warning("Backtest stats failed for %s: %s", symbol, e)

        try:
            session = MarketSession.objects.create(**data)
            _country_future_counter.assign_sequence(session)
            
            logger.debug(f"Created {symbol} session: {session.last_price}")
            return session
        except Exception as e:
            logger.error(f"Session creation failed for {symbol}: {e}", exc_info=True)
            return None
    
    def create_session_for_total(self, composite, session_number, capture_group, time_info, country, ym_entry_price=None):
        """Create one MarketSession row for TOTAL composite"""
        composite_signal = (composite.get('composite_signal') or 'HOLD').upper()
        
        data = {
            'session_number': session_number,
            'capture_group': capture_group,
            'year': time_info['year'],
            'month': time_info['month'],
            'date': time_info['date'],
            'day': time_info['day'],
            'country': country,
            'future': 'TOTAL',
            'captured_at': timezone.now(),
            # Removed legacy wndw field
            
            # TOTAL-specific composite data
            'weighted_average': self.safe_decimal(composite.get('avg_weighted')),
            'instrument_count': composite.get('count') or 11,
            'bhs': composite_signal,
            'weight': composite.get('signal_weight_sum'),
            # Removed legacy study_fw field
        }

        if ym_entry_price is not None and composite_signal not in ['HOLD', '']:
            data['entry_price'] = ym_entry_price
            high, low = compute_targets_for_symbol('YM', ym_entry_price)
            data['target_high'] = high
            data['target_low'] = low

        # ---------- Backtest stats: use existing service ----------
        try:
            stats = compute_backtest_stats_for_country_future(
                country=country,
                future='TOTAL',
                as_of=data['captured_at'],
            )
            data.update(stats)
        except Exception as e:
            logger.warning("Backtest stats failed for TOTAL: %s", e)
        
        try:
            session = MarketSession.objects.create(**data)
            _country_future_counter.assign_sequence(session)
            
            logger.info(f"TOTAL session: {data['weighted_average']:.4f} -> {composite_signal}" if data['weighted_average'] else f"TOTAL: {composite_signal}")
            return session
        except Exception as e:
            logger.error(f"TOTAL session creation failed: {e}", exc_info=True)
            return None
    
    @transaction.atomic
    def capture_market_open(self, market):
        """Create MarketSession rows at market open (one per future + TOTAL).

        Early-return if market-level capture flags disable futures or open capture.
        """
        # Belt-and-suspenders guard (monitor should already filter, but we re-check)
        display_country = getattr(market, 'country', None)
        country_code = normalize_country_code(display_country) or display_country

        if not getattr(market, 'enable_futures_capture', True):
            logger.info("Futures capture disabled for %s; skipping.", country_code or display_country or '?')
            return None
        if not getattr(market, 'enable_open_capture', True):
            logger.info("Open capture disabled for %s; skipping.", country_code or display_country or '?')
            return None
        try:
            logger.info(f"Capturing {country_code or display_country or '?'} market open...")
            
            enriched, composite = get_enriched_quotes_with_composite()
            if not enriched:
                logger.error(f"No enriched rows for {country_code or display_country or '?'}")
                return None
            # Filter to this country and expected symbols only
            allowed_symbols = set([s.lstrip('/') for s in FUTURES_SYMBOLS])
            enriched = [
                r for r in enriched
                if (r.get('country') == (country_code or display_country))
                and (r.get('instrument', {}).get('symbol') or '').lstrip('/') in allowed_symbols
            ]
            if not enriched:
                logger.error(f"No enriched rows for {country_code or display_country or '?'} after country/symbol filter")
                return None
            composite_signal = (composite.get('composite_signal') or 'HOLD').upper()
            
            time_info = market.get_current_market_time()
            try:
                sym_list = [r.get('instrument', {}).get('symbol') for r in enriched]
                logger.info(
                    "MarketOpenCapture %s %04d-%02d-%02d - enriched count=%s, symbols=%s",
                    country_code or display_country or '?',
                    time_info['year'],
                    time_info['month'],
                    time_info['date'],
                    len(enriched),
                    sym_list,
                )
            except Exception:
                logger.info(
                    "MarketOpenCapture %s %04d-%02d-%02d - enriched count=%s",
                    country_code or display_country or '?',
                    time_info['year'],
                    time_info['month'],
                    time_info['date'],
                    len(enriched),
                )
            session_number = self.get_next_session_number()
            # Derive next capture_group (canonical session identity)
            with transaction.atomic():
                last_group_val = (
                    MarketSession.objects.exclude(capture_group__isnull=True)
                    .aggregate(max_group=Max('capture_group'))
                    .get('max_group')
                ) or 0
                capture_group = int(last_group_val) + 1
            
            # Create 11 future sessions
            sessions_created = []
            failures = []
            ym_entry_price = None
            for row in enriched:
                symbol = row['instrument']['symbol']
                session = self.create_session_for_future(
                    symbol, row, session_number, capture_group, time_info, country_code or display_country, composite_signal
                )
                if session:
                    sessions_created.append(session)
                else:
                    failures.append(symbol)
                base_symbol = symbol.lstrip('/').upper()
                if base_symbol == 'YM' and composite_signal not in ['HOLD', '']:
                    if composite_signal in ['BUY', 'STRONG_BUY']:
                        ym_entry_price = self.safe_decimal(row.get('ask'))
                    elif composite_signal in ['SELL', 'STRONG_SELL']:
                        ym_entry_price = self.safe_decimal(row.get('bid'))
            
            # Create TOTAL session
            total_session = self.create_session_for_total(
                composite, session_number, capture_group, time_info, country_code or display_country, ym_entry_price=ym_entry_price
            )
            if total_session:
                sessions_created.append(total_session)

            # ?? Populate market_open from last_price for this session
            try:
                MarketOpenMetric.update_for_capture_group(capture_group)

            except Exception as metrics_error:
                logger.warning(
                    "market_open refresh failed for session %s: %s",
                    session_number,
                    metrics_error,
                    exc_info=True,
                )

            # ?? Refresh aggregate metrics so downstream dashboards stay in sync.
            #     Each helper runs best-effort so reporting does not block captures.

            try:
                # Only update WNDW totals for THIS session & THIS market
                _country_future_wndw_service.update_for_capture_group(
                    capture_group=capture_group,
                    country=country_code or display_country,
                )
            except Exception as stats_error:
                logger.warning(
                    "Failed country/future WNDW totals refresh after capture %s: %s",
                    session_number,
                    stats_error,
                    exc_info=True,
                )
            
            logger.info(
                "Capture complete: %s Session #%s, created=%s%s",
                country_code or display_country or '?',
                session_number,
                len(sessions_created),
                (f", failures={failures}" if failures else ""),
            )
            return sessions_created[0] if sessions_created else None
            
        except Exception as e:
            logger.error(f"Capture failed for {country_code or display_country or '?'}: {e}", exc_info=True)
            return None


_service = MarketOpenCaptureService()
_country_future_counter = CountryFutureCounter()
_country_future_wndw_service = CountryFutureWndwTotalsService()



def capture_market_open(market):
    return _service.capture_market_open(market)

__all__ = ['capture_market_open', 'MarketOpenCaptureService']

