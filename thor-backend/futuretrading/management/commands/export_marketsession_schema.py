from django.core.management.base import BaseCommand
from django.conf import settings
from FutureTrading.models.MarketSession import MarketSession
import csv
from pathlib import Path


class Command(BaseCommand):
    help = "Export MarketSession model field names and types to CSV and stdout"

    def add_arguments(self, parser):
        parser.add_argument('--out', type=str, default='export/MarketSession_schema.csv',
                            help='Output CSV path relative to thor-backend root')

    def handle(self, *args, **options):
        fields = [
            (f.name, getattr(f, 'get_internal_type', lambda: type(f).__name__)())
            for f in MarketSession._meta.get_fields()
            if getattr(f, 'concrete', False) and not getattr(f, 'many_to_many', False)
        ]
        # Print to stdout
        self.stdout.write('name,type')
        for name, ftype in fields:
            self.stdout.write(f"{name},{ftype}")
        # Write CSV
        out_rel = options['out']
        base_dir = Path(getattr(settings, 'BASE_DIR', Path(__file__).resolve().parents[3]))
        out_path = (base_dir / out_rel).resolve()
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open('w', newline='') as fp:
                w = csv.writer(fp)
                w.writerow(['name', 'type'])
                w.writerows(fields)
            self.stdout.write(self.style.SUCCESS(f"Wrote schema CSV to {out_path}"))
        except Exception as e:
            self.stderr.write(f"Failed to write CSV: {e}")
            raise SystemExit(1)
