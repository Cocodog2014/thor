Check market_open
cd A:\Thor\thor-backend; python manage.py market_open_capture --force --country USA
python manage.py market_open_capture --country USA
forces a market_open even when it already did one
python manage.py market_open_capture --country USA --force

python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('AAPL'))"

cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id <your_user_id> --equities VFF --futures ""
PS A:\Thor\thor-backend> python manage.py schwab_stream --user-id 1 --equities VFF --futures ""
>
cd A:\Thor\thor-backend
python manage.py schwab_stream --user-id 1 --equities VFF --futures ""
python manage.py schwab_stream --user-id 1 --equities VFF


A) Check Redis has live data

In another terminal:

python manage.py shell -c "from LiveData.shared.redis_client import live_data_redis; print(live_data_redis.get_latest_quote('VFF'))"


If you see a dict (price, symbol, country=GLOBAL), Schwab → Redis is live ✅

clean tokens cd A:\Thor\thor-backend
python manage.py shell -c "from LiveData.schwab.models import BrokerConnection; bc=BrokerConnection.objects.filter(user_id=1, broker='SCHWAB').first(); 
assert bc, 'No Schwab BrokerConnection for user 1';
bc.access_token=''; bc.refresh_token=''; bc.access_expires_at=0; bc.save(update_fields=['access_token','refresh_token','access_expires_at','updated_at']);
print('Cleared tokens for', bc.id)"