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



***check opening a closing of markets:

        Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/global-markets/markets/ | Select-Object -Expand Content

    Note: backend server needs to be running 

Open different pages in Thor-trading:

Global Market:
    https://dev-thor.360edu.org/app/global

    https://dev-thor.360edu.org/app/home




