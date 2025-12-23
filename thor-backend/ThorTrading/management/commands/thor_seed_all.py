"""
thor_seed_all
-----------------
Purpose:
- Seeds baseline, canonical configuration data for Thor. This is NOT a backup of live/session data.
- Populates/refreshes GlobalMarkets entries and prepares placeholders for futures universe and default weights.

What it seeds today:
- Markets (from `seed_markets.json`)
- Futures and default weights: detected but not yet wired to concrete models; left as placeholders until model is finalized.

Intended use cases:
- Fresh environment setup after clone or DB rebuild.
- Disaster recovery to restore authoritative defaults.
- Keep dev/staging/prod aligned on market definitions.

Input files (JSON fixtures):
- `seed_markets.json`
- `seed_futures.json` (optional, pending instruments model wiring)
- `seed_default_weights.json` (optional, pending weights model wiring)

Default data directory:
- By default, the command looks for a `data` folder relative to this app path.
- Recommended location for fixtures: `A:\Thor\thor-backend\data`.
- You can override with `--data-dir`.

Examples (PowerShell):
- Run with default:
    `Push-Location A:\Thor\thor-backend; python manage.py thor_seed_all; Pop-Location`
- Run with explicit data dir:
    `Push-Location A:\Thor\thor-backend; python manage.py thor_seed_all --data-dir "A:\\Thor\\thor-backend\\data"; Pop-Location`

Notes:
- This command does not modify or restore historical `MarketSession` rows.
- It does not touch Redis or live quote streams.
"""
from django.core.management.base import BaseCommand
import json
import os

from GlobalMarkets.models.market import Market
from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES
from ThorTrading.services.config.country_codes import normalize_country_code
try:
    from ThorTrading.models import instruments  # placeholder if a dedicated instruments model exists
except Exception:
    instruments = None


class Command(BaseCommand):
    help = "Seed Thor baseline data (markets, futures configs, weights)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"),
            help="Directory containing seed JSON files",
        )

    def handle(self, *args, **options):
        data_dir = options["data_dir"]
        self.stdout.write(self.style.NOTICE(f"Seeding from {data_dir}"))

        # Build a case-insensitive map of canonical market keys
        canonical_map = {c.lower(): c for c in ALLOWED_CONTROL_COUNTRIES}

        markets_path = os.path.join(data_dir, "seed_markets.json")
        if os.path.exists(markets_path):
            with open(markets_path, "r", encoding="utf-8") as f:
                markets = json.load(f)
            created, updated = 0, 0
            for m in markets:
                raw_name = m.get("name")
                normalized = normalize_country_code(raw_name)
                canonical = canonical_map.get(normalized.lower()) if normalized else None
                if not canonical:
                    self.stdout.write(self.style.WARNING(f"Skipping unknown market key: {raw_name!r}"))
                    continue

                obj, is_created = Market.objects.update_or_create(
                    country=canonical,
                    defaults={
                        "timezone_name": m.get("timezone"),
                        "is_control_market": m.get("is_control_market", True),
                        "enable_futures_capture": m.get("enable_futures_capture", True),
                        "enable_open_capture": m.get("enable_open_capture", True),
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1
            self.stdout.write(self.style.SUCCESS(f"Markets seeded: created={created}, updated={updated}"))
        else:
            self.stdout.write(self.style.WARNING("seed_markets.json not found; skipping Markets."))

        # Futures universe (optional wiring depending on actual model)
        futures_path = os.path.join(data_dir, "seed_futures.json")
        if os.path.exists(futures_path):
            try:
                with open(futures_path, "r", encoding="utf-8") as f:
                    futures = json.load(f)
                # If you have a dedicated instruments model/table, wire it here.
                if instruments is None:
                    self.stdout.write(self.style.NOTICE("seed_futures.json found; no instruments model wired. Skipping."))
                else:
                    # Example: instruments.Instrument.update_or_create(...)
                    self.stdout.write(self.style.NOTICE("Seeding futures to instruments model (implementation TBD)."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed seeding futures: {e}"))
        else:
            self.stdout.write(self.style.NOTICE("seed_futures.json not found; skipping futures."))

        weights_path = os.path.join(data_dir, "seed_default_weights.json")
        if os.path.exists(weights_path):
            self.stdout.write(self.style.NOTICE("Default weights fixture present (apply when model is confirmed)."))
        else:
            self.stdout.write(self.style.NOTICE("seed_default_weights.json not found; skipping weights."))

        self.stdout.write(self.style.SUCCESS("Thor seed complete."))

