from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse, HttpRequest
from django.utils.timezone import now
import json
import time
from .redis_client import get_redis, latest_key, unified_stream_key

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
