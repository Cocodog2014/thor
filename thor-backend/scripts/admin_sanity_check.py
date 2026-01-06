import os
import sys
import django
from datetime import datetime, date

# Initialize Django
# Ensure backend root is on sys.path
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from Instruments.models.market_24h import MarketTrading24Hour
from Instruments.models.intraday import InstrumentIntraday


def run():
    # Create or get a 24h session
    sess, created = MarketTrading24Hour.objects.get_or_create(
            session_number=1,
        symbol='ES',
        defaults={
            'session_date': date.today(),
            'open_price_24h': 5100.00,
            'prev_close_24h': 5080.00,
            'low_24h': 5090.00,
            'high_24h': 5120.00,
            'range_diff_24h': 30.00,
            'range_pct_24h': 30.00 / 5100.00 * 100.0,
            'finalized': False,
        }
    )
    print(f"24h session: id={sess.id}, created={created}, symbol={sess.symbol}")

    # Create a 1-minute bar (instrument-scoped)
    bar = InstrumentIntraday.objects.create(
        timestamp_minute=datetime.utcnow().replace(second=0, microsecond=0),
        symbol='ES',
        open_1m=5110.00,
        high_1m=5112.00,
        low_1m=5108.50,
        close_1m=5111.25,
        volume_1m=1234,
    )
    print(f"Intraday bar: id={bar.id}, symbol={bar.symbol}, ts={bar.timestamp_minute}")


if __name__ == '__main__':
    run()

