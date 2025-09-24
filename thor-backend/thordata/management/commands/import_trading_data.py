import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from thordata.models import TradingData, ImportJob
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import trading data from CleanData-ComputerLearning.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file to import'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually importing data'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # Validate file exists
        if not os.path.exists(csv_file):
            raise CommandError(f'File "{csv_file}" does not exist.')

        self.stdout.write(f'Starting import from: {csv_file}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be imported'))

        # Create import job for tracking
        import_job = ImportJob.objects.create(
            file_name=os.path.basename(csv_file),
            status='RUNNING',
            started_at=timezone.now()
        )

        try:
            # First pass: count total rows
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                total_rows = sum(1 for row in reader)
            
            import_job.total_rows = total_rows
            import_job.save()

            self.stdout.write(f'Total rows to import: {total_rows:,}')

            # Second pass: import data
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Map CSV headers to our model fields
                field_mapping = self._get_field_mapping(reader.fieldnames)
                
                batch = []
                processed = 0
                skipped = 0

                for row_num, row in enumerate(reader, 1):
                    try:
                        trading_data = self._create_trading_data(row, field_mapping)
                        if trading_data:
                            batch.append(trading_data)
                        else:
                            skipped += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error processing row {row_num}: {e}')
                        )
                        skipped += 1
                        continue

                    # Process batch
                    if len(batch) >= batch_size:
                        if not dry_run:
                            self._save_batch(batch)
                        processed += len(batch)
                        
                        # Update progress
                        import_job.processed_rows = processed
                        import_job.save()
                        
                        self.stdout.write(f'Processed: {processed:,}/{total_rows:,} rows')
                        batch = []

                # Process remaining batch
                if batch:
                    if not dry_run:
                        self._save_batch(batch)
                    processed += len(batch)

                # Final update
                import_job.processed_rows = processed
                import_job.status = 'COMPLETED' if not dry_run else 'DRY_RUN'
                import_job.finished_at = timezone.now()
                import_job.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Import completed! Processed: {processed:,}, Skipped: {skipped:,}'
                    )
                )

        except Exception as e:
            import_job.status = 'FAILED'
            import_job.error_message = str(e)
            import_job.finished_at = timezone.now()
            import_job.save()
            raise CommandError(f'Import failed: {e}')

    def _get_field_mapping(self, fieldnames):
        """Map CSV column names to model fields and additional_data."""
        # Core fields that map directly to model columns
        core_fields = {
            'No._Trades': 'no_trades',
            'DLST': 'dlst',
            'Year': 'year',
            'Month': 'month',
            'Date': 'date',
            'Day': 'day',
            'WorldOpen': 'open_price',        # Fixed: was 'OPEN' (market hours)
            'WorldClose': 'close_price',      # Fixed: was 'CLOSE' (market hours)
            'WorldHigh': 'world_high',        # Using existing field
            'WorldLow': 'world_low',          # Using existing field
            'Volume': 'volume',
            'WorldNetChange': 'world_net_change',
            'WorldNetPercChange': 'world_net_perc_change',
        }
        
        # All other fields go into additional_data JSON
        additional_fields = [
            field for field in fieldnames 
            if field not in core_fields and field.strip()
        ]
        
        return {
            'core_fields': core_fields,
            'additional_fields': additional_fields
        }

    def _create_trading_data(self, row, field_mapping):
        """Create TradingData instance from CSV row."""
        try:
            # Month name to number mapping
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            # Extract core fields
            core_data = {}
            for csv_field, model_field in field_mapping['core_fields'].items():
                value = row.get(csv_field, '').strip()
                if not value:
                    core_data[model_field] = None
                    continue
                
                # Convert types based on model field
                if model_field in ['no_trades', 'year', 'date']:
                    core_data[model_field] = int(value)
                elif model_field == 'month':
                    # Handle month name to number conversion
                    if value in month_map:
                        core_data[model_field] = month_map[value]
                    else:
                        # If it's already a number, use it
                        core_data[model_field] = int(value)
                elif model_field in ['open_price', 'close_price', 'world_high', 'world_low', 
                                   'world_net_change', 'world_net_perc_change']:
                    try:
                        core_data[model_field] = Decimal(value)
                    except (ValueError, InvalidOperation):
                        core_data[model_field] = None
                elif model_field == 'volume':
                    try:
                        core_data[model_field] = int(float(value)) if value else None
                    except (ValueError, TypeError):
                        core_data[model_field] = None
                else:
                    core_data[model_field] = value

            # Extract additional data for JSON field
            additional_data = {}
            for field in field_mapping['additional_fields']:
                value = row.get(field, '').strip()
                if value:
                    # Try to convert to number if possible
                    try:
                        if '.' in value:
                            additional_data[field] = float(value)
                        else:
                            additional_data[field] = int(value)
                    except ValueError:
                        additional_data[field] = value

            # Create TradingData instance
            trading_data = TradingData(
                **core_data,
                additional_data=additional_data
            )
            
            return trading_data

        except (ValueError, InvalidOperation) as e:
            self.stdout.write(
                self.style.WARNING(f'Skipping row with invalid data: {e}')
            )
            return None

    def _save_batch(self, batch):
        """Save batch of TradingData objects with transaction."""
        with transaction.atomic():
            TradingData.objects.bulk_create(
                batch, 
                ignore_conflicts=True,  # Skip duplicates based on unique_together
                batch_size=1000
            )