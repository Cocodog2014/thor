from django.core.management.base import BaseCommand
from futuretrading.models import TradingInstrument


class Command(BaseCommand):
    help = "Set display_precision for futures instruments (e.g. /YM -> 0 decimals)."

    # Define desired display precision per root symbol (without leading slash)
    PRECISION_MAP = {
        # Equity indices
        'YM': 0,      # Dow mini trades in whole points
        'ES': 2,      # Quarter points -> 2 decimals suffices (.25)
        'NQ': 2,      # Quarter points
        'RTY': 2,     # Tenth increments displayed with 2 decimals
        # Energies / Metals
        'CL': 2,      # .01
        'SI': 3,      # .005 -> show 3 decimals to avoid rounding away .005
        'HG': 4,      # 0.0005 typical tick
        'GC': 1,      # 0.10
        # Vol / FX / Rates
        'VX': 2,      # 0.01
        'DX': 2,      # 0.01
        'ZB': 2,      # 1/32 convention simplified to 2 decimals for now
    }

    def handle(self, *args, **options):
        updated = 0
        skipped = 0
        for root, precision in self.PRECISION_MAP.items():
            inst = TradingInstrument.objects.filter(symbol__in=[root, f'/{root}']).first()
            if not inst:
                self.stdout.write(self.style.WARNING(f"Missing instrument for {root}"))
                continue
            if inst.display_precision != precision:
                old = inst.display_precision
                inst.display_precision = precision
                inst.save(update_fields=['display_precision'])
                updated += 1
                self.stdout.write(f"Updated {inst.symbol}: {old} -> {precision}")
            else:
                skipped += 1
        self.stdout.write(self.style.SUCCESS(f"Display precision updated: {updated}, unchanged: {skipped}"))
