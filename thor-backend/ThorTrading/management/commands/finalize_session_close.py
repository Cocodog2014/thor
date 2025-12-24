from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.models.Martket24h import MarketTrading24Hour


class Command(BaseCommand):
    help = (
        "Copy 24h close from MarketTrading24Hour into MarketSession.close_24h at session close. "
        "Requires --country and --symbol (instrument code). Optionally --capture_group to override latest."
    )

    def add_arguments(self, parser):
        parser.add_argument('--country', required=True, help='Country code, e.g., USA, Japan, London')
        parser.add_argument('--symbol', required=True, help='Instrument code, e.g., ES, NQ, CL')
        parser.add_argument('--capture_group', type=int, help='Numeric capture_group to use; defaults to latest for country')

    def handle(self, *args, **options):
        country = options['country']
        symbol = options['symbol']
        capture_group = options.get('capture_group')

        # Resolve the target MarketSession via capture_group identity instead of timestamp heuristics
        if capture_group is not None:
            session = MarketSession.objects.filter(country=country, capture_group=capture_group).order_by('-id').first()
            if session is None:
                raise CommandError(f"No MarketSession found for country={country} capture_group={capture_group}.")
            group = capture_group
        else:
            session = (
                MarketSession.objects
                .filter(country=country)
                .exclude(capture_group__isnull=True)
                .order_by('-capture_group', '-id')
                .first()
            )
            if session is None:
                raise CommandError(f"No MarketSession with capture_group for country={country}.")
            group = session.capture_group

        # Get 24h row for instrument + group
        try:
            twentyfour = MarketTrading24Hour.objects.get(session_group=group, symbol=symbol)
        except MarketTrading24Hour.DoesNotExist:
            raise CommandError(
                f"No MarketTrading24Hour found for session_group={group} symbol={symbol}. Supervisor must populate it first."
            )

        close_val = twentyfour.close_24h
        if close_val is None:
            raise CommandError("MarketTrading24Hour.close_24h is None; cannot finalize session close.")

        with transaction.atomic():
            # Denormalize into MarketSession.close_24h and set a finalized timestamp if available
            session.close_24h = close_val
            # Optional: update captured_at to now to mark finalization
            session.captured_at = session.captured_at or timezone.now()
            session.save(update_fields=['close_24h', 'captured_at'])

        self.stdout.write(self.style.SUCCESS(
            f"Finalized session for {country} group={group}: close_24h={close_val} from {symbol}"
        ))

