schwab+++++++++++++++++++++++++++++++++++++++++++++++++

https://dev-thor.360edu.org/api/schwab/oauth/start/

USAMexico4

https://dev-thor.360edu.org/schwab/oauth/start/



Schwab API account info:

https://dev-thor.360edu.org/api/schwab/account/summary/

Schwab API Positions:

http://127.0.0.1:8000/api/schwab/account/positions/?account_number=60910485
https://dev-thor.360edu.org/api/schwab/account/positions/?account_number=60910485

Local

http://127.0.0.1:8000/api/schwab/account/summary/?account_number=60910485


Run Daphne pointing at your ASGI app:

python -m daphne -b 127.0.0.1 -p 8000 thor_project.asgi:application

cd A:\Thor\thor-backend
python -m daphne -b 0.0.0.0 -p 8000 thor_project.asgi:application

$env:THOR_REALTIME_FORCE="1"
python -m daphne -b 0.0.0.0 -p 8000 thor_project.asgi:application



