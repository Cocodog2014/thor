Check market_open
cd A:\Thor\thor-backend; python manage.py market_open_capture --force --country USA
python manage.py market_open_capture --country USA
forces a market_open even when it already did one
python manage.py market_open_capture --country USA --force

python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('AAPL'))"

Quick proof: does Redis have TSLA?

python manage.py shell -c "import time; from LiveData.shared.redis_client import live_data_redis; q=live_data_redis.get_latest_quote('TSLA'); print(q); now=time.time(); ts=float((q or {}).get('timestamp') or 0); print('age_seconds=', None if not q else round(now-ts,1)); print('age_abs_seconds=', None if not q else round(abs(now-ts),1))"

cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id 1


**If you want to see ticks for all instruments as they arrive, run:**

cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id 1 --echo-ticks

Note: `schwab_stream` auto-loads enabled symbols from the DB (and will fall back to the Instruments watchlist → auto-sync to SchwabSubscription). If you have no watchlist/subscriptions yet, pass `--equities` / `--futures`.

python manage.py schwab_stream --user-id 1 --equities VFF --futures ""
python manage.py schwab_stream --user-id 1 --equities GOOG
python manage.py schwab_stream --user-id 1 --equities NFLX
python manage.py schwab_stream --user-id 1 --equities NVDA
cls
.
Delete data from Redis:

cd A:\Thor\thor-backend
$env:THOR_STACK_AUTO_START='0'; $env:DJANGO_LOG_LEVEL='ERROR';
A:/Thor/.venv/Scripts/python.exe manage.py shell --verbosity 0 -c "from LiveData.shared.redis_client import live_data_redis as r; r.client.delete(r.LATEST_QUOTES_HASH); r.client.delete(r.ACTIVE_QUOTES_ZSET); print('cleared')"


Check Redis Data Base:

A:/Thor/.venv/Scripts/python.exe manage.py shell --verbosity 0 -c "from LiveData.shared.redis_client import live_data_redis as r; print(r.client.hlen(r.LATEST_QUOTES_HASH))"


A) Check Redis has live data

In another terminal:

1. python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('VFF'))"

Verify Redis is receiving ticks (new terminal)

2. cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('VFF'))"

cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('MSFT'))"

3. python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('YM'))"

4. cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('GOOG'))"

cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('NFLX'))"
python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('NVDA'))"



If you see a dict (price, symbol, country=GLOBAL), Schwab → Redis is live ✅

Notes
- A small negative `age_seconds` can happen (clock skew); use `age_abs_seconds`.
- A running `schwab_stream` can be updated live via Redis Pub/Sub control plane (no restart needed).

Control plane (live add/remove/set while `schwab_stream` is running)

Channel:
- `live_data:subscriptions:schwab:<user_id>`

Examples:

python manage.py shell -c "import json; from LiveData.shared.redis_client import live_data_redis; live_data_redis.client.publish('live_data:subscriptions:schwab:1', json.dumps({'action':'add','asset':'EQUITY','symbols':['TSLA']}))"

python manage.py shell -c "import json; from LiveData.shared.redis_client import live_data_redis; live_data_redis.client.publish('live_data:subscriptions:schwab:1', json.dumps({'action':'remove','asset':'EQUITY','symbols':['GOOG']}))"

python manage.py shell -c "import json; from LiveData.shared.redis_client import live_data_redis; live_data_redis.client.publish('live_data:subscriptions:schwab:1', json.dumps({'action':'set','asset':'FUTURE','symbols':['/ES']}))"

# Unsubscribe all equities:
python manage.py shell -c "import json; from LiveData.shared.redis_client import live_data_redis; live_data_redis.client.publish('live_data:schwab:control:1', json.dumps({'action':'set','asset':'EQUITY','symbols':[]}))"

# Unsubscribe all equities:
python manage.py shell -c "import json; from LiveData.shared.redis_client import live_data_redis; live_data_redis.client.publish('live_data:subscriptions:schwab:1', json.dumps({'action':'set','asset':'EQUITY','symbols':[]}))"

clean tokens cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.schwab.models import BrokerConnection; bc=BrokerConnection.objects.filter(user_id=1, broker='SCHWAB').first(); 
assert bc, 'No Schwab BrokerConnection for user 1';
bc.access_token=''; bc.refresh_token=''; bc.access_expires_at=0; bc.save(update_fields=['access_token','refresh_token','access_expires_at','updated_at']);
print('Cleared tokens for', bc.id)"