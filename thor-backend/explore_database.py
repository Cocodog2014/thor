import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from thordata.models import TradingData, ImportJob
from django.db import connection

print("=" * 60)
print("🔍 THOR TRADING DATABASE EXPLORER")
print("=" * 60)

# Database connection info
with connection.cursor() as cursor:
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"PostgreSQL Version: {version}")
    
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]
    print(f"Current Database: {db_name}")

print("\n" + "=" * 60)
print("📊 TABLE STATISTICS")
print("=" * 60)

# Record counts
trading_count = TradingData.objects.count()
import_count = ImportJob.objects.count()

print(f"TradingData Records: {trading_count:,}")
print(f"ImportJob Records: {import_count}")

print("\n" + "=" * 60)
print("📈 TRADING DATA OVERVIEW")
print("=" * 60)

# Data range
if trading_count > 0:
    earliest = TradingData.objects.order_by('year', 'month', 'date').first()
    latest = TradingData.objects.order_by('-year', '-month', '-date').first()
    
    print(f"Date Range: {earliest.year}-{earliest.month:02d}-{earliest.date:02d} to {latest.year}-{latest.month:02d}-{latest.date:02d}")
    
    # DLST types
    dlst_types = TradingData.objects.values_list('dlst', flat=True).distinct()
    print(f"DLST Types: {list(dlst_types)}")
    
    # Year distribution
    print("\nRecords by Year:")
    from django.db.models import Count
    year_counts = TradingData.objects.values('year').annotate(count=Count('id')).order_by('year')
    for item in year_counts:
        print(f"  {item['year']}: {item['count']:,} records")

print("\n" + "=" * 60)
print("📋 SAMPLE RECORDS")
print("=" * 60)

# Show first 3 records
print("First 3 Trading Records:")
for i, record in enumerate(TradingData.objects.all()[:3], 1):
    print(f"  {i}. {record}")
    print(f"     Open: ${record.open_price}, Close: ${record.close_price}, Volume: {record.volume}")
    print(f"     Additional Data Keys: {len(record.additional_data)} indicators")

print("\n" + "=" * 60)
print("📥 IMPORT HISTORY")
print("=" * 60)

# Import jobs
print("Recent Import Jobs:")
for job in ImportJob.objects.all()[:3]:
    print(f"  • {job.file_name}")
    print(f"    Status: {job.status}")
    print(f"    Progress: {job.processed_rows:,}/{job.total_rows:,}")
    if job.finished_at and job.started_at:
        duration = job.finished_at - job.started_at
        print(f"    Duration: {duration}")
    print()

print("=" * 60)
print("✅ Database exploration complete!")
print("=" * 60)

# Sample JSON data
sample = TradingData.objects.first()
if sample and sample.additional_data:
    print(f"\n🔍 Sample JSON Indicators (first 10):")
    for i, (key, value) in enumerate(list(sample.additional_data.items())[:10], 1):
        print(f"  {i:2d}. {key}: {value}")
    
    if len(sample.additional_data) > 10:
        print(f"  ... and {len(sample.additional_data) - 10} more indicators")

print(f"\n🌐 Access via Django Admin: http://127.0.0.1:8000/admin/")
print(f"📊 TradingData Admin: http://127.0.0.1:8000/admin/thordata/tradingdata/")
print(f"📥 ImportJob Admin: http://127.0.0.1:8000/admin/thordata/importjob/")