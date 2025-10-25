from __future__ import annotations

import logging
from typing import List
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .redis_client import live_data_redis

logger = logging.getLogger(__name__)


def _parse_symbols_param(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [s.strip().lstrip('/').upper() for s in raw.split(',') if s.strip()]


@api_view(['GET'])
def get_quotes_snapshot(request):
    """Return latest quotes snapshot from Redis for specified symbols.

    Query params:
      - symbols: comma separated list, e.g. YM,ES,NQ,RTY,CL,SI,HG,GC,VX,DX,ZB

    Response:
      {
        "quotes": [ {symbol, bid, ask, last, volume, ...}, ...],
        "count": n,
        "source": "redis_snapshot"
      }
    """
    symbols = _parse_symbols_param(request.GET.get('symbols'))

    if not symbols:
        return Response({
            'quotes': [],
            'count': 0,
            'source': 'redis_snapshot',
            'note': 'No symbols specified'
        }, status=status.HTTP_200_OK)

    try:
        quotes = live_data_redis.get_latest_quotes(symbols)
        return Response({
            'quotes': quotes,
            'count': len(quotes),
            'source': 'redis_snapshot'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Snapshot read failed: {e}")
        return Response({'error': 'Snapshot read failed', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
