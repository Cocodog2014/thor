"""Session volume accumulation job for heartbeat.

Tracks volume in the current market session at 5-15s intervals.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.intraday_supervisor.session_volume import update_session_volume_for_country


class SessionVolumeJob(Job):
    name = "session_volume"

    def __init__(self, interval_seconds: float = 10.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            enriched, _ = get_enriched_quotes_with_composite()
        except Exception:
            return

        if not enriched:
            return

        countries = set()
        for row in enriched:
            country = row.get("country")
            if country:
                countries.add(country)

        for country in countries:
            try:
                country_rows = [r for r in enriched if r.get("country") == country]
                update_session_volume_for_country(country, country_rows)
            except Exception:
                pass
