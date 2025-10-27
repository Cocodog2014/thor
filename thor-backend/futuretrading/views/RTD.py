"""
Real-Time Data (RTD) views

Moved from FutureTrading/views.py for clearer organization. The class
name stays the same so urls don't change.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import threading
import logging
import requests

from ..models import TradingInstrument
from ..config import EXPECTED_FUTURES
from LiveData.shared.redis_client import live_data_redis
from ..models.extremes import Rolling52WeekStats
from ..services.classification import enrich_quote_row, compute_composite
from ..services.metrics import compute_row_metrics

logger = logging.getLogger(__name__)


class LatestQuotesView(APIView):
    """
    API view that returns latest market data and signals for all active futures instruments
    with statistical values and weighted total composite score.
    
    Uses LiveData/tos endpoint to get TOS RTD Excel data.
    """

    def get(self, request):
        try:
            # Step 1: Nudge LiveData/TOS to refresh in the background so the next poll is fresh
            def _kick_refresh():
                try:
                    requests.get(
                        'http://localhost:8000/api/feed/tos/quotes/latest/',
                        params={'consumer': 'futures_trading'},
                        timeout=3
                    )
                except requests.exceptions.RequestException:
                    # Non-fatal: we still serve from current Redis snapshot
                    pass

            threading.Thread(target=_kick_refresh, daemon=True).start()

            # Step 2: Source of truth = Redis snapshot populated by LiveData app
            # Read the latest quotes for our expected instruments.
            # If Redis is empty/stale, trigger a refresh from the TOS endpoint once and retry.
            raw_quotes = []

            # Symbols as stored by the producer (Excel). Some require mapping from our canonical names.
            redis_symbol_map = {
                # Canonical -> Redis key symbol
                'DX': '$DXY',
            }
            fetch_symbols = [redis_symbol_map.get(sym, sym) for sym in EXPECTED_FUTURES]

            def read_from_redis():
                quotes = live_data_redis.get_latest_quotes(fetch_symbols)
                return quotes or []

            # First attempt: read what's already in Redis
            raw_quotes = read_from_redis()

            # If Redis has too few items, trigger a refresh (fallback) and try once more
            if len(raw_quotes) < max(1, int(len(fetch_symbols) * 0.7)):
                try:
                    requests.get(
                        'http://localhost:8000/api/feed/tos/quotes/latest/',
                        params={'consumer': 'futures_trading'},
                        timeout=5
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(f"TOS refresh failed: {e}")
                # Retry read
                raw_quotes = read_from_redis()

            # Step 2: Transform TOS quotes into FutureTrading structure (instrument + fields)
            instruments_db = {inst.symbol: inst for inst in TradingInstrument.objects.all()}
            
            # Load 52-week stats from database
            stats_52w = {s.symbol: s for s in Rolling52WeekStats.objects.all()}

            transformed_rows = []
            for idx, quote in enumerate(raw_quotes):
                raw_symbol = quote.get('symbol', '')

                # Normalize symbol - fix common Excel RTD symbol mismatches
                symbol_map = {
                    'RT': 'RTY',
                    '30YrBond': 'ZB',
                    '30Yr T-BOND': 'ZB',
                    'T-BOND': 'ZB',
                    # Dollar Index varieties from Excel/feeds
                    '$DXY': 'DX',
                    'DXY': 'DX',
                    'USDX': 'DX',
                }
                symbol = symbol_map.get(raw_symbol, raw_symbol)

                db_inst = instruments_db.get(symbol) or instruments_db.get(f'/{symbol}')
                display_precision = db_inst.display_precision if db_inst else 2
                tick_value = str(db_inst.tick_value) if db_inst and db_inst.tick_value else None
                margin_requirement = str(db_inst.margin_requirement) if db_inst and db_inst.margin_requirement else None

                def to_str(val):
                    return str(val) if val is not None else None
                
                # Get 52w stats for this symbol (if exists)
                symbol_52w = stats_52w.get(symbol)
                high_52w = to_str(symbol_52w.high_52w) if symbol_52w else None
                low_52w = to_str(symbol_52w.low_52w) if symbol_52w else None

                row = {
                    'instrument': {
                        'id': idx + 1,
                        'symbol': symbol,
                        'name': symbol,
                        'exchange': 'TOS',
                        'currency': 'USD',
                        'display_precision': display_precision,
                        'tick_value': tick_value,
                        'margin_requirement': margin_requirement,
                        'is_active': True,
                        'sort_order': idx
                    },
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
                    'last_size': None,
                    'market_status': 'CLOSED',
                    'data_source': 'TOS_RTD',
                    'is_real_time': True,
                    'delay_minutes': 0,
                    'timestamp': quote.get('timestamp'),
                    'extended_data': {
                        'high_52w': high_52w,  # From database, not Excel
                        'low_52w': low_52w,    # From database, not Excel
                    }
                }
                transformed_rows.append(row)

            # Step 3: Apply classification and metrics
            enriched_rows = []
            for row in transformed_rows:
                enrich_quote_row(row)
                try:
                    metrics = compute_row_metrics(row)
                    row.update(metrics)
                    if row.get('change_percent') in (None, '', '—'):
                        row['change_percent'] = metrics.get('last_prev_pct')
                except Exception as e:
                    logger.warning(
                        f"Metric computation failed for {row.get('instrument',{}).get('symbol','?')}: {e}")
                enriched_rows.append(row)

            # Step 4: Composite
            total_data = compute_composite(enriched_rows)

            return Response({'rows': enriched_rows, 'total': total_data}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in LatestQuotesView: {str(e)}")
            return Response({'error': 'Internal server error', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
