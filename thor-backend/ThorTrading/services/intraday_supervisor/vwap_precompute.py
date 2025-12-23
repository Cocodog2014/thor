import os
from django.utils import timezone
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.services.indicators.vwap import vwap_service


def precompute_rolling_vwap(symbols):
    window_minutes = int(os.getenv('ROLLING_VWAP_WINDOW_MINUTES', '30'))
    now_dt = timezone.now().replace(second=0, microsecond=0)
    vwap_payload = {}
    for sym in symbols:
        try:
            val = vwap_service.calculate_rolling_vwap(sym, window_minutes, now_dt=now_dt)
            vwap_payload[sym] = {
                'raw': float(val) if val is not None else None,
                'text': str(val) if val is not None else None,
            }
        except Exception:
            vwap_payload[sym] = {'raw': None, 'text': None}

    live_data_redis.set_json(
        f"rolling_vwap:{window_minutes}",
        {
            'window_minutes': window_minutes,
            'as_of': now_dt.isoformat(),
            'values': vwap_payload,
        },
        ex=120,
    )

