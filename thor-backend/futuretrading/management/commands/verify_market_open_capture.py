from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from typing import Optional

from FutureTrading.models import MarketOpenSession


class Command(BaseCommand):
    help = (
        "Inspect a MarketOpenSession and its FutureSnapshot records to verify capture fields.\n"
        "Prints per-future signal, weight, last/change/change%, 24h range, 52w range, and TOTAL composite."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=int,
            help="Specific MarketOpenSession ID to inspect (default: latest by captured_at)",
        )
        parser.add_argument(
            "--country",
            type=str,
            help="Filter to a specific country (if multiple sessions exist today)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show all available fields for each snapshot",
        )

    def handle(self, *args, **options):
        session: Optional[MarketOpenSession] = None
        session_id = options.get("session_id")
        country = options.get("country")
        verbose = options.get("verbose")

        qs = MarketOpenSession.objects.all()
        if country:
            qs = qs.filter(country__iexact=country)
        if session_id:
            qs = qs.filter(id=session_id)
        session = qs.order_by("-captured_at").first()

        if not session:
            raise CommandError("No MarketOpenSession found with the specified criteria.")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Session: id={session.id} country={session.country} date={session.year}-{session.month:02d}-{session.date:02d} captured={session.captured_at}"
        ))
        self.stdout.write(
            f"YM bid/ask/last: {session.ym_bid} / {session.ym_ask} / {session.ym_last}; total_signal={session.total_signal}; fw_weight={session.fw_weight}"
        )

        futures = list(session.futures.order_by("symbol"))
        total = next((f for f in futures if f.symbol == "TOTAL"), None)
        rows = [f for f in futures if f.symbol != "TOTAL"]

        if total:
            self.stdout.write(self.style.HTTP_INFO(
                f"TOTAL → signal={total.signal or '—'} weighted_average={total.weighted_average or '—'} sum_weighted={total.sum_weighted or '—'} count={total.instrument_count or '—'} weight={total.weight or '—'}"
            ))
        else:
            self.stdout.write(self.style.WARNING("No TOTAL snapshot found."))

        def fmt(val):
            return "—" if val is None or val == "" else str(val)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_LABEL("Per-future snapshots:"))
        for snap in rows:
            line = (
                f"{snap.symbol:<4} last={fmt(snap.last_price)} change={fmt(snap.change)} pct={fmt(snap.change_percent)} "
                f"signal={fmt(snap.signal)} weight={fmt(snap.weight)} "
                f"24h={fmt(snap.day_24h_low)}-{fmt(snap.day_24h_high)} range={fmt(snap.range_high_low)} r%={fmt(snap.range_percent)} "
                f"52w={fmt(snap.week_52_low)}-{fmt(snap.week_52_high)}"
            )
            self.stdout.write(line)
            if verbose:
                extra = (
                    f"  bid/ask={fmt(snap.bid)}/{fmt(snap.ask)} sizes={fmt(snap.bid_size)}/{fmt(snap.ask_size)} vol={fmt(snap.volume)} vwap={fmt(snap.vwap)}\n"
                    f"  open/close={fmt(snap.open)}/{fmt(snap.close)} open_vs_prev={fmt(snap.open_vs_prev_number)} ({fmt(snap.open_vs_prev_percent)}) spread={fmt(snap.spread)}\n"
                    f"  entry/targets={fmt(snap.entry_price)} hi/lo={fmt(snap.high_dynamic)}/{fmt(snap.low_dynamic)}"
                )
                self.stdout.write(extra)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Verification complete."))
