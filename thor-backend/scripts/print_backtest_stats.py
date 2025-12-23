"""Quick diagnostic to print backtest stats for selected symbols.

Run with:
    python manage.py runscript print_backtest_stats   (if django-extensions installed)
Or simply:
    python scripts/print_backtest_stats.py

Ensures Django is initialized then calls compute_backtest_stats_for_country_future.
"""

import os
import sys
import django

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
try:
    django.setup()
except Exception as e:
    print("Failed Django setup:", e)
    raise

from ThorTrading.services.analytics.backtest_stats import compute_backtest_stats_for_country_future

SYMBOLS = ["YM", "ES", "NQ", "TOTAL"]
DEFAULT_COUNTRY = os.environ.get("BACKTEST_STATS_COUNTRY", "USA")

def main(country: str = DEFAULT_COUNTRY):
    for sym in SYMBOLS:
        stats = compute_backtest_stats_for_country_future(
            country=country,
            future=sym,
        )
        print(f"{country} / {sym}: {stats}")

if __name__ == "__main__":
    arg_country = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_COUNTRY
    main(arg_country)

