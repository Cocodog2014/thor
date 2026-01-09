cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id 1


**If you want to see ticks for all instruments as they arrive, run:**

cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id 1 --echo-ticks

Note: `schwab_stream` auto-loads enabled symbols from the DB (and will fall back to the Instruments watchlist → auto-sync to SchwabSubscription). If you have no watchlist/subscriptions yet, pass `--equities` / `--futures`.

Delete data from Redis:

cd A:\Thor\thor-backend
$env:THOR_STACK_AUTO_START='0'; $env:DJANGO_LOG_LEVEL='ERROR';
A:/Thor/.venv/Scripts/python.exe manage.py shell --verbosity 0 -c "from LiveData.shared.redis_client import live_data_redis as r; r.client.delete(r.LATEST_QUOTES_HASH); r.client.delete(r.ACTIVE_QUOTES_ZSET); print('cleared')"


Check Redis Data Base:

A:/Thor/.venv/Scripts/python.exe manage.py shell --verbosity 0 -c "from LiveData.shared.redis_client import live_data_redis as r; print(r.client.hlen(r.LATEST_QUOTES_HASH))"



clean tokens:

cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.schwab.models import BrokerConnection; bc=BrokerConnection.objects.filter(user_id=1, broker='SCHWAB').first(); 
assert bc, 'No Schwab BrokerConnection for user 1';
bc.access_token=''; bc.refresh_token=''; bc.access_expires_at=0; bc.save(update_fields=['access_token','refresh_token','access_expires_at','updated_at']);
print('Cleared tokens for', bc.id)"



PS A:\Thor\thor-backend> python manage.py shell -c "
>> from GlobalMarkets.models import Market
>> from GlobalMarkets.services import compute_market_status
>> from django.utils import timezone
>> 
>> now = timezone.now()
>> print('UTC now:', now)
>> 
>> for key in ['pre_usa','usa']:
>>     m = Market.objects.get(key=key)
>>     print('\n---', m.key, m.name, '---')
>>     print('tz:', m.timezone_name, 'open:', m.open_time, 'close:', m.close_time, 'status(db):', m.status)
>>     res = compute_market_status(m, now_utc=now)
>>     print('computed:', res)
>> "
[2026-01-09 09:48:58,711] [INFO] thor_project.apps: 🔥 Thor platform ready: initializing realtime stack (platform app)...
[2026-01-09 09:48:58,711] [INFO] thor_project.realtime.runtime: ⏭️ Skipping realtime heartbeat during management command.
[2026-01-09 09:48:58,711] [INFO] thor_project.apps: 🚀 Thor realtime stack started (platform app).
25 objects imported automatically (use -v 2 for details).

UTC now: 2026-01-09 16:48:58.725117+00:00

--- pre_usa Pre USA ---
tz: America/New_York open: 08:30:00 close: 16:00:00 status(db): CLOSED
computed: MarketComputation(status=Market.Status.OPEN, next_transition_utc=datetime.datetime(2026, 1, 9, 21, 0, tzinfo=datetime.timezone.utc), reason='open')

--- usa USA ---
tz: America/New_York open: 09:30:00 close: 16:00:00 status(db): CLOSED
computed: MarketComputation(status=Market.Status.OPEN, next_transition_utc=datetime.datetime(2026, 1, 9, 21, 0, tzinfo=datetime.timezone.utc), reason='open')
PS A:\Thor\thor-backend> 



***check opening a closing of markets:

        Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/global-markets/markets/ | Select-Object -Expand Content

    Note: backend server needs to be running 


