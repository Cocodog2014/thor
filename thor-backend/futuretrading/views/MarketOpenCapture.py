"""
Market Open Capture - Single-Table Design

Captures futures data at market open using the same enrichment pipeline as the live RTD endpoint.
Creates 12 MarketOpenSession rows per market open (one per future + TOTAL).
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from FutureTrading.models.MarketSession import MarketSession
from FutureTrading.models.extremes import Rolling52WeekStats
from FutureTrading.models.target_high_low import TargetHighLowConfig
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.services.classification import enrich_quote_row, compute_composite
from FutureTrading.services.metrics import compute_row_metrics

logger = logging.getLogger(__name__)


class MarketOpenCaptureService:
    """Captures futures data at market open - matches RTD endpoint logic exactly"""
    
    FUTURES_SYMBOLS = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']
    REDIS_SYMBOL_MAP = {'DX': '$DXY'}
    SYMBOL_NORMALIZE_MAP = {
        'RT': 'RTY', '30YrBond': 'ZB', '30Yr T-BOND': 'ZB', 'T-BOND': 'ZB',
        '$DXY': 'DX', 'DXY': 'DX', 'USDX': 'DX'
    }
    
    def get_next_session_number(self):
        last = MarketSession.objects.order_by('-session_number').first()
        return (last.session_number + 1) if last else 1
    
    def fetch_redis_quotes(self):
        quotes = {}
        for symbol in self.FUTURES_SYMBOLS:
            key = self.REDIS_SYMBOL_MAP.get(symbol, symbol)
            try:
                data = live_data_redis.get_latest_quote(key)
                if data:
                    quotes[symbol] = data
            except Exception as e:
                logger.error(f"Redis fetch failed for {symbol}: {e}")
        return quotes
    
    def build_enriched_rows(self, redis_quotes):
        stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}
        rows = []
        
        for idx, symbol in enumerate(self.FUTURES_SYMBOLS):
            quote = redis_quotes.get(symbol)
            if not quote:
                continue
            
            norm_sym = self.SYMBOL_NORMALIZE_MAP.get(symbol, symbol)
            sym_52w = stats_52w.get(norm_sym)
            
            to_str = lambda v: str(v) if v is not None else None
            
            row = {
                'instrument': {'id': idx+1, 'symbol': norm_sym, 'name': norm_sym, 'exchange': 'TOS', 
                              'currency': 'USD', 'display_precision': 2, 'is_active': True, 'sort_order': idx},
                'price': to_str(quote.get('last')),
                'last': to_str(quote.get('last')),
                'bid': to_str(quote.get('bid')),
                'ask': to_str(quote.get('ask')),
                'volume': quote.get('volume'),
                'open_price': to_str(quote.get('open')),
                'high_price': to_str(quote.get('high')),
                'low_price': to_str(quote.get('low')),
                'close_price': to_str(quote.get('close')),
                'previous_close': to_str(quote.get('close')),
                'change': to_str(quote.get('change')),
                'change_percent': None,
                'vwap': None,
                'bid_size': quote.get('bid_size'),
                'ask_size': quote.get('ask_size'),
                'extended_data': {
                    'high_52w': str(sym_52w.high_52w) if (sym_52w and sym_52w.high_52w) else None,
                    'low_52w': str(sym_52w.low_52w) if (sym_52w and sym_52w.low_52w) else None
                }
            }
            
            enrich_quote_row(row)
            try:
                metrics = compute_row_metrics(row)
                row.update(metrics)
                if row.get('change_percent') in (None, '', ''):
                    row['change_percent'] = metrics.get('last_prev_pct')
            except Exception as e:
                logger.warning(f"Metrics failed for {norm_sym}: {e}")
            
            rows.append(row)
        return rows
    
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
        """Create one MarketOpenSession row for a single future"""
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
            'wndw': 'PENDING',
            
            # Live price data at open
            'last_price': self.safe_decimal(row.get('last')),
            'change': self.safe_decimal(row.get('change')),
            'change_percent': self.safe_decimal(row.get('change_percent') or row.get('last_prev_pct')),
            'session_ask': self.safe_decimal(row.get('ask')),
            'ask_size': self.safe_int(row.get('ask_size')),
            'session_bid': self.safe_decimal(row.get('bid')),
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
            'study_fw': 'HBS',
        }
        
        # Calculate entry and targets using configurable offsets
        if composite_signal and composite_signal not in ['HOLD', '']:
            if composite_signal in ['BUY', 'STRONG_BUY']:
                data['entry_price'] = data.get('session_ask')
            elif composite_signal in ['SELL', 'STRONG_SELL']:
                data['entry_price'] = data.get('session_bid')

            entry = data.get('entry_price')
            if entry:
                # Look up per-symbol target config (prefetched earlier into self._target_cfg_cache)
                cfg = getattr(self, '_target_cfg_cache', {}).get(symbol.upper())
                if cfg:
                    try:
                        targets = cfg.compute_targets(entry)
                        if targets:
                            high, low = targets
                            data['target_high'] = high
                            data['target_low'] = low
                        else:
                            # Disabled config: do not set targets (leave null)
                            logger.debug(f"Target config disabled for {symbol}; skipping targets")
                    except Exception as e:
                        logger.warning(f"Target config compute failed for {symbol}: {e}; falling back to legacy defaults")
                        data['target_high'] = entry + 20
                        data['target_low'] = entry - 20
                else:
                    # No config present: legacy fallback
                    data['target_high'] = entry + 20
                    data['target_low'] = entry - 20
        
        try:
            session = MarketSession.objects.create(**data)
            logger.debug(f"Created {symbol} session: {session.last_price}")
            return session
        except Exception as e:
            logger.error(f"Session creation failed for {symbol}: {e}", exc_info=True)
            return None
    
    def create_session_for_total(self, composite, session_number, time_info, country):
        """Create one MarketOpenSession row for TOTAL composite"""
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
            'wndw': 'PENDING',
            
            # TOTAL-specific composite data
            'weighted_average': self.safe_decimal(composite.get('avg_weighted')),
            'instrument_count': composite.get('count') or 11,
            'bhs': composite_signal,
            'weight': composite.get('signal_weight_sum'),
            'study_fw': 'TOTAL'
        }
        
        try:
            session = MarketSession.objects.create(**data)
            logger.info(f"TOTAL session: {data['weighted_average']:.4f} -> {composite_signal}" if data['weighted_average'] else f"TOTAL: {composite_signal}")
            return session
        except Exception as e:
            logger.error(f"TOTAL session creation failed: {e}", exc_info=True)
            return None
    
    @transaction.atomic
    def capture_market_open(self, market):
        """
        Captures market open by creating 12 MarketOpenSession rows:
        - 11 rows for individual futures (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB)
        - 1 row for TOTAL composite
        
        All rows share same session_number, country, date/time info.
        """
        try:
            logger.info(f"Capturing {market.country} market open...")
            
            # Prefetch target high/low configs for all symbols (single query)
            self._target_cfg_cache = {c.symbol.upper(): c for c in TargetHighLowConfig.objects.filter(is_active=True)}

            redis_quotes = self.fetch_redis_quotes()
            if not redis_quotes:
                logger.error(f"No quotes for {market.country}")
                return None
            
            enriched = self.build_enriched_rows(redis_quotes)
            if not enriched:
                logger.error(f"No enriched rows for {market.country}")
                return None
            
            composite = compute_composite(enriched)
            composite_signal = (composite.get('composite_signal') or 'HOLD').upper()
            
            time_info = market.get_current_market_time()
            session_number = self.get_next_session_number()
            
            # Create 11 future sessions
            sessions_created = []
            for row in enriched:
                symbol = row['instrument']['symbol']
                session = self.create_session_for_future(
                    symbol, row, session_number, time_info, market.country, composite_signal
                )
                if session:
                    sessions_created.append(session)
            
            # Create TOTAL session
            total_session = self.create_session_for_total(
                composite, session_number, time_info, market.country
            )
            if total_session:
                sessions_created.append(total_session)
            
            logger.info(f"Capture complete: Session #{session_number}, {len(sessions_created)} rows created")
            return sessions_created[0] if sessions_created else None
            
        except Exception as e:
            logger.error(f"Capture failed for {market.country}: {e}", exc_info=True)
            return None


_service = MarketOpenCaptureService()

def capture_market_open(market):
    return _service.capture_market_open(market)

__all__ = ['capture_market_open', 'MarketOpenCaptureService']
