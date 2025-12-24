# Generated manually to add country to TradingInstrument and VwapMinute, with backfill then enforce non-null
from django.db import migrations, models

COUNTRY_CHOICES = [
    ("Canada", "Canada"),
    ("China", "China"),
    ("Germany", "Germany"),
    ("India", "India"),
    ("Japan", "Japan"),
    ("Mexico", "Mexico"),
    ("Pre_USA", "Pre_USA"),
    ("USA", "USA"),
    ("United Kingdom", "United Kingdom"),
]


def backfill_country(apps, schema_editor):
    TradingInstrument = apps.get_model("ThorTrading", "TradingInstrument")
    VwapMinute = apps.get_model("ThorTrading", "VwapMinute")

    # Use a safe default until per-row assignment is known; align with prior backfill
    TradingInstrument.objects.filter(country__isnull=True).update(country="USA")
    VwapMinute.objects.filter(country__isnull=True).update(country="USA")


def noop_reverse(apps, schema_editor):
    # No-op reverse; leaving data intact
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0015_targethighlowconfig_country_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="tradinginstrument",
            name="country",
            field=models.CharField(
                choices=COUNTRY_CHOICES,
                db_index=True,
                help_text="Market region (canonical values only)",
                max_length=32,
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="vwapminute",
            name="country",
            field=models.CharField(
                choices=COUNTRY_CHOICES,
                db_index=True,
                help_text="Market region (canonical values only)",
                max_length=32,
                null=True,
                blank=True,
            ),
        ),
        migrations.RunPython(backfill_country, noop_reverse),
        migrations.AlterField(
            model_name="tradinginstrument",
            name="country",
            field=models.CharField(
                choices=COUNTRY_CHOICES,
                db_index=True,
                help_text="Market region (canonical values only)",
                max_length=32,
                null=False,
                blank=False,
            ),
        ),
        migrations.AlterField(
            model_name="vwapminute",
            name="country",
            field=models.CharField(
                choices=COUNTRY_CHOICES,
                db_index=True,
                help_text="Market region (canonical values only)",
                max_length=32,
                null=False,
                blank=False,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="tradinginstrument",
            unique_together={("country", "symbol")},
        ),
        migrations.AlterUniqueTogether(
            name="vwapminute",
            unique_together={("country", "symbol", "timestamp_minute")},
        ),
        migrations.AddIndex(
            model_name="tradinginstrument",
            index=models.Index(fields=["country", "symbol"], name="idx_instr_country_symbol"),
        ),
        migrations.AddIndex(
            model_name="tradinginstrument",
            index=models.Index(fields=["country", "is_active"], name="idx_instr_country_active"),
        ),
        migrations.AddIndex(
            model_name="tradinginstrument",
            index=models.Index(fields=["category", "sort_order"], name="idx_instr_category_sort"),
        ),
        migrations.AddIndex(
            model_name="vwapminute",
            index=models.Index(fields=["country", "symbol", "timestamp_minute"], name="idx_vwap_cty_sym_ts"),
        ),
        migrations.AddIndex(
            model_name="vwapminute",
            index=models.Index(fields=["timestamp_minute"], name="idx_vwap_ts"),
        ),
    ]
