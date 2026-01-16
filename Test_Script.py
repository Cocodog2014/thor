1.  query Redis for the live_data:lock:schwab_stream:1 key
        
    Script: cd A:\Thor\thor-backend; $env:THOR_STACK_AUTO_START='0'; $env:DJANGO_LOG_LEVEL='ERROR'; python manage.py shell --verbosity 0 -c "from LiveData.shared.redis_client import live_data_redis as r; k='live_data:lock:schwab_stream:1'; print('exists', r.client.exists(k)); print('type', r.client.type(k)); print('ttl', r.client.ttl(k)); print('get', r.client.get(k))"

    Note: The schwab_stream lock key exists right now: exists 1
    It’s a string with ttl 45 seconds and owner token Thor:65308   