import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from thordata.models import TradingData, ImportJob

# Check data
print(f"Total TradingData records: {TradingData.objects.count():,}")
print(f"Total ImportJob records: {ImportJob.objects.count()}")

# Show sample records
print("\nFirst 3 TradingData records:")
for td in TradingData.objects.all()[:3]:
    print(f"  {td}")

# Show latest import job
print("\nLatest ImportJob:")
latest_job = ImportJob.objects.first()
if latest_job:
    print(f"  {latest_job}")
    print(f"  Status: {latest_job.status}")
    print(f"  Processed: {latest_job.processed_rows:,}/{latest_job.total_rows:,}")

# Show some stats
print("\nData Statistics:")
print(f"  Unique DLST values: {TradingData.objects.values('dlst').distinct().count()}")
print(f"  Date range: {TradingData.objects.aggregate(min_year=django.db.models.Min('year'), max_year=django.db.models.Max('year'))}")

# Show sample additional_data
sample = TradingData.objects.first()
if sample:
    print(f"\nSample additional_data keys (first 10): {list(sample.additional_data.keys())[:10]}")