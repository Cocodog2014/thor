from django.core.management.base import BaseCommand
from django.conf import settings
from ThorTrading.models.MarketSession import MarketSession
import csv
from pathlib import Path


class Command(BaseCommand):
    help = "Export MarketSession model field names and types to CSV and stdout"

    def add_arguments(self, parser):
        parser.add_argument(
            '--out',
            type=str,
            default='export/MarketSession_schema.csv',
            help='Output CSV path relative to thor-backend root',
        )
        parser.add_argument(
            '--absolute',
            action='store_true',
            help='Treat --out as an absolute path (skip BASE_DIR join)',
        )

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
        out_arg = options['out']
        if options.get('absolute'):
            out_path = Path(out_arg).expanduser().resolve()
        else:
            base_dir = Path(getattr(settings, 'BASE_DIR', Path(__file__).resolve().parents[3]))
            out_path = (base_dir / out_arg).resolve()
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

