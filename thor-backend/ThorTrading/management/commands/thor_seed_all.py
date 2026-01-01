from __future__ import annotations
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
import os

from ThorTrading.studies.futures_total.command_logic.thor_seed_all import run


class Command(BaseCommand):
    help = "Seed Thor baseline data (markets, futures configs, weights)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"),
            help="Directory containing seed JSON files",
        )
        parser.add_argument(
            "--include-futures",
            action="store_true",
            help="Seed futures from seed_futures.json (requires instruments model wiring).",
        )
        parser.add_argument(
            "--include-weights",
            action="store_true",
            help="Seed default weights from seed_default_weights.json (requires model wiring).",
        )

    def handle(self, *args, **options):
        run(
            data_dir=options["data_dir"],
            include_futures=bool(options.get("include_futures", False)),
            include_weights=bool(options.get("include_weights", False)),
            stdout=self.stdout,
            style=self.style,
        )

