"""Inspect current position data in both live and paper databases."""
from django.core.management.base import BaseCommand
from ActAndPos.live.models import LivePosition
from ActAndPos.paper.models import PaperPosition


def _fmt(value, fmt: str) -> str:
    if value is None:
        return "-"
    try:
        return format(value, fmt)
    except Exception:
        return str(value)


class Command(BaseCommand):
    help = "Inspect position P/L fields in both live and paper databases"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, help="Filter by user ID")
        parser.add_argument("--broker-account", help="Filter by broker account ID")
        parser.add_argument("--account-key", help="Filter by paper account key")

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        broker_account = options.get("broker_account")
        account_key = options.get("account_key")

        self.stdout.write(self.style.SUCCESS("\n=== LIVE POSITIONS ==="))
        live_qs = LivePosition.objects.all()
        if user_id:
            live_qs = live_qs.filter(user_id=user_id)
        if broker_account:
            live_qs = live_qs.filter(broker_account_id=broker_account)

        if live_qs.exists():
            for pos in live_qs.order_by("symbol"):
                self.stdout.write(
                    f"  {pos.symbol:8} | "
                    f"qty={_fmt(pos.quantity, '8.2f')} | "
                    f"avg={_fmt(pos.avg_price, '10.2f')} | "
                    f"mark={_fmt(pos.mark_price, '10.2f')} | "
                    f"pl_day={_fmt(pos.broker_pl_day, '10.2f')} | "
                    f"pl_ytd={_fmt(pos.broker_pl_ytd, '10.2f')}"
                )
        else:
            self.stdout.write("  (no live positions)")

        self.stdout.write(self.style.SUCCESS("\n=== PAPER POSITIONS ==="))
        paper_qs = PaperPosition.objects.all()
        if user_id:
            paper_qs = paper_qs.filter(user_id=user_id)
        if account_key:
            paper_qs = paper_qs.filter(account_key=account_key)

        if paper_qs.exists():
            for pos in paper_qs.order_by("symbol"):
                self.stdout.write(
                    f"  {pos.symbol:8} | "
                    f"qty={_fmt(pos.quantity, '8.2f')} | "
                    f"avg={_fmt(pos.avg_price, '10.2f')} | "
                    f"mark={_fmt(pos.mark_price, '10.2f')} | "
                    f"pl_day={_fmt(pos.realized_pl_day, '10.2f')} | "
                    f"pl_total={_fmt(pos.realized_pl_total, '10.2f')}"
                )
        else:
            self.stdout.write("  (no paper positions)")

        self.stdout.write(self.style.SUCCESS("\n✓ Done\n"))
