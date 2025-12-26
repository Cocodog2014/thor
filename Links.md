Check market_open
cd A:\Thor\thor-backend; python manage.py market_open_capture --force --country USA
python manage.py market_open_capture --country USA
forces a market_open even when it already did one
python manage.py market_open_capture --country USA --force

