"""Capture VWAP minute snapshots.

Reads latest quotes from Redis and stores one row per symbol per minute
in `VwapMinute`. No VWAP math performed here; this is a raw data feed
for downstream VWAP calculations.

Usage:
    python manage.py capture_vwap_minutes            # default 60s interval
    python manage.py capture_vwap_minutes --interval 10

Interval < 60s simply increases sampling granularity; persistence only
occurs when the minute changes.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from ThorTrading.studies.futures_total.command_logic.capture_vwap_minutes import run


class Command(BaseCommand):
    help = "Capture per-minute VWAP source rows (raw Redis snapshots)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Sampling interval seconds (default: 60). Persistence still minute-based.",
        )

    def handle(self, *args, **options):
        run(interval=int(options["interval"]), stdout=self.stdout, style=self.style)
