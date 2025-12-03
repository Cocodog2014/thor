"""Utility to load GlobalMarkets.Market rows from data/seed_markets.json."""
from __future__ import annotations

import json
from datetime import datetime
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
django.setup()

from GlobalMarkets.models import Market  # noqa: E402

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed_markets.json")


def main() -> int:
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        markets = json.load(fh)

    created = 0
    updated = 0
    for entry in markets:
        country = entry["name"]
        open_time = datetime.strptime(entry["open_time"], "%H:%M").time()
        close_time = datetime.strptime(entry["close_time"], "%H:%M").time()
        defaults = {
            "timezone_name": entry["timezone"],
            "market_open_time": open_time,
            "market_close_time": close_time,
            "weight": entry.get("weight", 0) / 100.0,
            "status": "CLOSED",
            "is_control_market": entry.get("is_control_market", True),
            "enable_futures_capture": entry.get("enable_futures_capture", True),
            "enable_open_capture": entry.get("enable_open_capture", True),
            "enable_close_capture": entry.get("enable_close_capture", True),
        }
        obj, is_created = Market.objects.update_or_create(
            country=country,
            defaults=defaults,
        )
        if is_created:
            created += 1
        else:
            updated += 1
    print(f"Markets created={created}, updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
