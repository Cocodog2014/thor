from django.db import migrations

FIELD_RENAMES = (
    ("market_high_percentage", "market_high_pct_open"),
    ("market_low_number", "market_low_open"),
    ("market_low_percentage", "market_low_pct_open"),
    ("market_close_number", "market_close"),
    ("market_close_percentage_high", "market_high_pct_close"),
    ("market_close_percentage_low", "market_low_pct_close"),
    ("market_range_number", "market_range"),
    ("market_range_percentage", "market_range_pct"),
)


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0077_marketsession_market_high_open"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name=old,
            new_name=new,
        )
        for old, new in FIELD_RENAMES
    ]
