"""
Market Open Capture - Single-Table Design

Captures futures data at market open using the same enrichment pipeline as the live RTD endpoint.
Creates 12 MarketSession rows per market open (one per future + TOTAL).
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from FutureTrading.models.MarketSession import MarketSession
from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.TargetHighLow import compute_targets_for_symbol
from FutureTrading.services.country_future_counts import update_country_future_stats



logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
    """Captures futures data at market open - matches RTD endpoint logic exactly.

    Uses centralized constants from FutureTrading.constants.
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
    
    def create_session_for_future(self, symbol, row, session_number, time_info, country, composite_signal):
        """Create one MarketSession row for a single future"""
        ext = row.get('extended_data', {})
        
        # Base session data
        data = {
            'session_number': session_number,
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
            'change': self.safe_decimal(row.get('change')),
            'change_percent': self.safe_decimal(row.get('change_percent') or row.get('last_prev_pct')),
            'ask_price': self.safe_decimal(row.get('ask')),
            'ask_size': self.safe_int(row.get('ask_size')),
            'bid_price': self.safe_decimal(row.get('bid')),
            'bid_size': self.safe_int(row.get('bid_size')),
            'volume': self.safe_int(row.get('volume')),
            'vwap': self.safe_decimal(row.get('vwap')),
            'spread': self.safe_decimal(row.get('spread')),
            
            # Session price data
            'session_open': self.safe_decimal(row.get('open_price')),
            'session_close': self.safe_decimal(row.get('close_price') or row.get('previous_close')),
            'open_vs_prev_number': self.safe_decimal(row.get('open_prev_diff')),
            'open_vs_prev_percent': self.safe_decimal(row.get('open_prev_pct')),
            
            # Range data
            'day_24h_low': self.safe_decimal(row.get('low_price')),
            'day_24h_high': self.safe_decimal(row.get('high_price')),
            'range_high_low': self.safe_decimal(row.get('range_diff')),
            'range_percent': self.safe_decimal(row.get('range_pct')),
            'week_52_low': self.safe_decimal(ext.get('low_52w')),
            'week_52_high': self.safe_decimal(ext.get('high_52w')),
            
            # Signal (individual future's signal from HBS)
            'bhs': (ext.get('signal') or '').upper() if ext.get('signal') else '',
            'weight': self.safe_int(ext.get('signal_weight')),
            # Removed legacy study_fw field (framework identifier no longer stored)
        }
        
        # Default values when there is no trade signal
        data['entry_price'] = None
        data['target_high'] = None
        data['target_low'] = None

        # Determine entry price based on composite signal, then compute targets centrally
        if composite_signal and composite_signal not in ['HOLD', '']:
            if composite_signal in ['BUY', 'STRONG_BUY']:
                data['entry_price'] = data.get('ask_price')
            elif composite_signal in ['SELL', 'STRONG_SELL']:
                data['entry_price'] = data.get('bid_price')
            entry = data['entry_price']
            if entry:
                high, low = compute_targets_for_symbol(symbol, entry)
                data['target_high'] = high
                data['target_low'] = low
        
        try:
            session = MarketSession.objects.create(**data)
            logger.debug(f"Created {symbol} session: {session.last_price}")
            return session
        except Exception as e:
            logger.error(f"Session creation failed for {symbol}: {e}", exc_info=True)
            return None
    
    def create_session_for_total(self, composite, session_number, time_info, country, ym_entry_price=None):
        """Create one MarketSession row for TOTAL composite"""
        composite_signal = (composite.get('composite_signal') or 'HOLD').upper()
        
        data = {
            'session_number': session_number,
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
        
        try:
            session = MarketSession.objects.create(**data)
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
        if not getattr(market, 'enable_futures_capture', True):
            logger.info("Futures capture disabled for %s; skipping.", market.country)
            return None
        if not getattr(market, 'enable_open_capture', True):
            logger.info("Open capture disabled for %s; skipping.", market.country)
            return None
        try:
            logger.info(f"Capturing {market.country} market open...")
            
            enriched, composite = get_enriched_quotes_with_composite()
            if not enriched:
                logger.error(f"No enriched rows for {market.country}")
                return None
            composite_signal = (composite.get('composite_signal') or 'HOLD').upper()
            
            time_info = market.get_current_market_time()
            session_number = self.get_next_session_number()
            
            # Create 11 future sessions
            sessions_created = []
            ym_entry_price = None
            for row in enriched:
                symbol = row['instrument']['symbol']
                session = self.create_session_for_future(
                    symbol, row, session_number, time_info, market.country, composite_signal
                )
                if session:
                    sessions_created.append(session)
                base_symbol = symbol.lstrip('/').upper()
                if base_symbol == 'YM' and composite_signal not in ['HOLD', '']:
                    if composite_signal in ['BUY', 'STRONG_BUY']:
                        ym_entry_price = self.safe_decimal(row.get('ask'))
                    elif composite_signal in ['SELL', 'STRONG_SELL']:
                        ym_entry_price = self.safe_decimal(row.get('bid'))
            
            # Create TOTAL session
            total_session = self.create_session_for_total(
                composite, session_number, time_info, market.country, ym_entry_price=ym_entry_price
            )
            if total_session:
                sessions_created.append(total_session)

            # 🔹 Refresh aggregate country/future metrics so downstream dashboards stay in sync.
            #     We wrap this in a best-effort block so a logging/reporting hiccup never breaks captures.
            try:
                update_country_future_stats()
            except Exception as stats_error:
                logger.warning(
                    "Country/future stats refresh failed after capture %s: %s",
                    session_number,
                    stats_error,
                    exc_info=True,
                )
            
            logger.info(f"Capture complete: Session #{session_number}, {len(sessions_created)} rows created")
            return sessions_created[0] if sessions_created else None
            
        except Exception as e:
            logger.error(f"Capture failed for {market.country}: {e}", exc_info=True)
            return None


_service = MarketOpenCaptureService()



def capture_market_open(market):
    return _service.capture_market_open(market)

__all__ = ['capture_market_open', 'MarketOpenCaptureService']
