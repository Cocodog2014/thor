from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse, HttpRequest
from django.utils.timezone import now
import json
import math
import time
from .redis_client import get_redis, latest_key, unified_stream_key
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from decimal import Decimal, InvalidOperation
from ThorTrading.services.vwap import vwap_service
from LiveData.shared.redis_client import live_data_redis
from django.db import connection

def _safe_float(value):
    """Convert DB numerics to float, skipping NaN/Inf payloads."""
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError, InvalidOperation):
        try:
            as_float = float(Decimal(value))
        except (InvalidOperation, TypeError, ValueError):
            return None
    if math.isnan(as_float) or math.isinf(as_float):
        return None
    return as_float


def _safe_int(value):
    """Convert DB numerics to int, avoiding NaN / overflow crashes."""
    as_float = _safe_float(value)
    if as_float is None:
        return None
    try:
        return int(as_float)
    except (ValueError, OverflowError):
        return None


@api_view(['GET'])
def session(request: HttpRequest):
    """
    GET /api/session?market=Tokyo&future=YM

    Returns session payload including latest 1-minute intraday bar for the
    given market (market_code) and future symbol from table `intraday_1m`.

    Response shape (partial):
    {
      "market": "Tokyo",
      "future": "YM",
      "intraday_latest": {
        "open": float | null,
        "high": float | null,
        "low": float | null,
        "close": float | null,
        "volume": int | null,
        "spread": float | null
      }
    }
    """
    market_code = (request.GET.get('market') or '').strip()
    future = (request.GET.get('future') or '').strip().upper()

    if not market_code or not future:
        return Response({
            'detail': 'Both market and future parameters are required.',
            'market': market_code,
            'future': future,
            'intraday_latest': None,
        }, status=status.HTTP_400_BAD_REQUEST)

    # Query latest 1-minute bar
    sql = (
        """
        SELECT open_1m, high_1m, low_1m, close_1m, volume_1m, spread_last
        FROM intraday_1m
        WHERE market_code = %s AND future = %s
        ORDER BY timestamp_minute DESC
        LIMIT 1
        """
    )

    latest = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, [market_code, future])
            row = cursor.fetchone()
            if row:
                open_v, high_v, low_v, close_v, volume_v, spread_v = row
                latest = {
                    'open': _safe_float(open_v),
                    'high': _safe_float(high_v),
                    'low': _safe_float(low_v),
                    'close': _safe_float(close_v),
                    'volume': _safe_int(volume_v),
                    'spread': _safe_float(spread_v),
                }
    except Exception as e:
        return Response({'detail': f'Database error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Minimal payload; hooks exist to merge session tiles when available
    payload = {
        'market': market_code,
        'future': future,
        'intraday_latest': latest,
    }

    return Response(payload, status=status.HTTP_200_OK)

@api_view(['GET'])
def vwap_today(request: HttpRequest):
    """GET /api/vwap/today?symbols=ES,YM

    Returns current session VWAP for requested comma-separated symbols.
    If symbols param omitted returns empty list. VWAP values may be null
    if insufficient data (no rows yet).
    Response shape: [{symbol, vwap, as_of}] with vwap as string or null.
    """
    symbols_param = request.GET.get('symbols') or ''
    symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
    out = []
    now_iso = now().isoformat()
    for sym in symbols:
        try:
            val = vwap_service.get_today_vwap(sym)
            out.append({
                'symbol': sym,
                'vwap': f"{val}" if val is not None else None,
                'as_of': now_iso,
            })
        except Exception as e:
            out.append({'symbol': sym, 'vwap': None, 'error': str(e), 'as_of': now_iso})
    return Response(out, status=status.HTTP_200_OK)

@api_view(['GET'])
def vwap_rolling(request: HttpRequest):
    """GET /api/vwap/rolling?symbols=ES,YM&minutes=30

    Returns rolling VWAP for each symbol over the last `minutes` window.
    If a precomputed Redis payload exists (written by IntradayMarketSupervisor)
    it is used; otherwise falls back to on-demand calculation.
    """
    symbols_param = request.GET.get('symbols') or ''
    minutes_param = request.GET.get('minutes') or '30'
    try:
        window_minutes = int(minutes_param)
    except Exception:
        window_minutes = 30
    symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
    out = []
    now_iso = now().isoformat()
    # Try precomputed hash
    redis_key = f"rolling_vwap:{window_minutes}"
    cached = live_data_redis.client.get(redis_key)
    cached_payload = None
    if cached:
        try:
            cached_payload = json.loads(cached)
        except Exception:
            cached_payload = None
    for sym in symbols:
        val = None
        if cached_payload and cached_payload.get('values'):
            val_str = cached_payload['values'].get(sym)
            val = Decimal(val_str) if val_str is not None else None
        if val is None:
            # Fallback compute
            try:
                val = vwap_service.calculate_rolling_vwap(sym, window_minutes)
            except Exception as e:
                out.append({'symbol': sym, 'vwap': None, 'error': str(e), 'window_minutes': window_minutes, 'as_of': now_iso})
                continue
        out.append({'symbol': sym, 'vwap': f"{val}" if val is not None else None, 'window_minutes': window_minutes, 'as_of': now_iso})
    return Response(out, status=status.HTTP_200_OK)

# API Overview
@api_view(['GET'])
def api_overview(request):
    """
    API Overview endpoint that provides information about available endpoints
    """
    api_urls = {
        'Overview': '/api/',
        'Statistics': '/api/stats/',
        'Quotes Snapshot': '/api/quotes?symbols=ES,YM',
        'Quotes Stream (SSE)': '/api/quotes/stream',
        'WorldClock': '/api/worldclock/',
        'Admin': '/admin/',
    }
    return Response(api_urls)

# Statistics endpoint
@api_view(['GET'])
def api_statistics(request):
    """
    Get statistics about the Thor application
    """
    # Return zeros/None for removed domains (backward compatible shape)
    stats = {
        'total_heroes': 0,
        'total_quests': 0,
        'completed_quests': 0,
        'total_artifacts': 0,
        'most_powerful_hero': None,
        'latest_quest': None,
    }
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
def quotes_snapshot(request: HttpRequest):
    """
    GET /api/quotes?symbols=ES,YM
    Returns latest snapshot for requested symbols from Redis latest-hash keys.
    If no symbols are provided, returns an empty list.
    """
    symbols_param = request.GET.get('symbols') or ''
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return Response([], status=status.HTTP_200_OK)

    r = get_redis()
    out = []
    for sym in symbols:
        data = r.hgetall(latest_key(sym))
        if data:
            # ensure types for common fields when possible
            for num in ('last', 'bid', 'ask'):
                if num in data and data[num] not in (None, ''):
                    try:
                        data[num] = float(data[num])
                    except Exception:
                        pass
            for num in ('lastSize', 'bidSize', 'askSize'):
                if num in data and data[num] not in (None, ''):
                    try:
                        data[num] = int(float(data[num]))
                    except Exception:
                        pass
            data['symbol'] = sym
            out.append(data)
    return Response(out, status=status.HTTP_200_OK)


def _sse_format(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, separators=(',', ':'))
    return f"event: {event}\n" f"data: {payload}\n\n"


@api_view(['GET'])
def quotes_stream(request: HttpRequest):
    """
    GET /api/quotes/stream
    Server-Sent Events stream reading from unified Redis Stream.
    Emits 'quote' events and periodic 'ping' heartbeats.
    """
    r = get_redis()
    stream_key = unified_stream_key()

    # Start at the end by default; use ?from=0-0 to replay
    from_id = request.GET.get('from', '$')
    heartbeat_interval = 10

    def event_generator():
        last_heartbeat = time.time()
        next_id = from_id
        # Initial hello
        yield _sse_format('hello', {'ts': now().isoformat()})
        while True:
            try:
                resp = r.xread({stream_key: next_id}, block=5000, count=100)
                if resp:
                    # resp: [(stream, [(id, {fields})...])]
                    for _, entries in resp:
                        for entry_id, fields in entries:
                            next_id = entry_id
                            # Try to coerce numbers for common fields
                            for k in ('last', 'bid', 'ask'):
                                if k in fields:
                                    try:
                                        fields[k] = float(fields[k])
                                    except Exception:
                                        pass
                            yield _sse_format('quote', {**fields, 'id': entry_id})
                # heartbeat
                if time.time() - last_heartbeat >= heartbeat_interval:
                    last_heartbeat = time.time()
                    yield _sse_format('ping', {'ts': now().isoformat()})
            except GeneratorExit:
                break
            except Exception as e:
                yield _sse_format('error', {'message': str(e)})
                time.sleep(1.0)

    resp = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'  # nginx friendly if used later
    return resp



