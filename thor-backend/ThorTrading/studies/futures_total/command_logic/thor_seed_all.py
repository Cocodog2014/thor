from __future__ import annotations

import json
import os

from GlobalMarkets.models.constants import ALLOWED_CONTROL_COUNTRIES
from GlobalMarkets.models.market import Market
from ThorTrading.services.config.country_codes import normalize_country_code


def run(
    *,
    data_dir: str,
    include_futures: bool,
    include_weights: bool,
    stdout,
    style,
) -> None:
    stdout.write(style.NOTICE(f"Seeding from {data_dir}"))

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
                stdout.write(style.WARNING(f"Skipping unknown market key: {raw_name!r}"))
                continue

            _, is_created = Market.objects.update_or_create(
                country=canonical,
                defaults={
                    "timezone_name": m.get("timezone"),
                    "enable_session_capture": m.get("enable_session_capture", True),
                    "enable_open_capture": m.get("enable_open_capture", True),
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1
        stdout.write(style.SUCCESS(f"Markets seeded: created={created}, updated={updated}"))
    else:
        stdout.write(style.WARNING("seed_markets.json not found; skipping Markets."))

    futures_path = os.path.join(data_dir, "seed_futures.json")
    if include_futures:
        if os.path.exists(futures_path):
            try:
                from ThorTrading.models import instruments  # placeholder if exists
            except Exception:
                instruments = None

            if instruments is None:
                stdout.write(style.NOTICE("Futures requested but no instruments model wired; skipping."))
            else:
                try:
                    with open(futures_path, "r", encoding="utf-8") as f:
                        futures = json.load(f)
                    stdout.write(
                        style.NOTICE(
                            f"Loaded {len(futures)} futures rows; implement model wiring before use."
                        )
                    )
                except Exception as exc:
                    stdout.write(style.WARNING(f"Failed reading futures fixture: {exc}"))
        else:
            stdout.write(style.NOTICE("--include-futures passed but seed_futures.json not found; skipping."))
    else:
        stdout.write(style.NOTICE("Skipping futures (enable with --include-futures)."))

    weights_path = os.path.join(data_dir, "seed_default_weights.json")
    if include_weights:
        if os.path.exists(weights_path):
            stdout.write(style.NOTICE("Weights fixture present; apply once model wiring is available."))
        else:
            stdout.write(style.NOTICE("--include-weights passed but seed_default_weights.json not found; skipping."))
    else:
        stdout.write(style.NOTICE("Skipping weights (enable with --include-weights)."))

    stdout.write(style.SUCCESS("Thor seed complete."))
