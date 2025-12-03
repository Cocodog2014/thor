from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.models.Martket24h import FutureTrading24Hour


class Command(BaseCommand):
    help = (
        "Copy 24h close from FutureTrading24Hour into MarketSession.close_24h at session close. "
        "Requires --country and --future (instrument code). Optionally --capture_group to override latest."
    )

    def add_arguments(self, parser):
        parser.add_argument('--country', required=True, help='Country code, e.g., USA, Japan, London')
        parser.add_argument('--future', required=True, help='Instrument code, e.g., ES, NQ, CL')
        parser.add_argument('--capture_group', type=int, help='Numeric capture_group to use; defaults to latest for country')

    def handle(self, *args, **options):
        country = options['country']
        future = options['future']
        capture_group = options.get('capture_group')

        # Resolve the target MarketSession
        session_qs = MarketSession.objects.filter(country=country).order_by('-captured_at')
        if not session_qs.exists():
            raise CommandError(f"No MarketSession found for country={country}. Open capture must run first.")

        session = session_qs.first()
        group = capture_group if capture_group is not None else session.capture_group
        if group is None:
            raise CommandError("MarketSession.capture_group is None; cannot resolve 24h session group.")

        # Get 24h row for instrument + group
        try:
            twentyfour = FutureTrading24Hour.objects.get(session_group=group, future=future)
        except FutureTrading24Hour.DoesNotExist:
            raise CommandError(
                f"No FutureTrading24Hour found for session_group={group} future={future}. Supervisor must populate it first."
            )

        close_val = twentyfour.close_24h
        if close_val is None:
            raise CommandError("FutureTrading24Hour.close_24h is None; cannot finalize session close.")

        with transaction.atomic():
            # Denormalize into MarketSession.close_24h and set a finalized timestamp if available
            session.close_24h = close_val
            # Optional: update captured_at to now to mark finalization
            session.captured_at = session.captured_at or timezone.now()
            session.save(update_fields=['close_24h', 'captured_at'])

        self.stdout.write(self.style.SUCCESS(
            f"Finalized session for {country} group={group}: close_24h={close_val} from {future}"
        ))

