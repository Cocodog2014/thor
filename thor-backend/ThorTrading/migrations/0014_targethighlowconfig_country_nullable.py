# Generated manually to make TargetHighLowConfig.country temporarily nullable for backfill
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0013_rename_future_symbol"),
    ]

    operations = [
        migrations.AddField(
            model_name="targethighlowconfig",
            name="country",
            field=models.CharField(
                choices=[
                    ("Canada", "Canada"),
                    ("China", "China"),
                    ("Germany", "Germany"),
                    ("India", "India"),
                    ("Japan", "Japan"),
                    ("Mexico", "Mexico"),
                    ("Pre_USA", "Pre_USA"),
                    ("USA", "USA"),
                    ("United Kingdom", "United Kingdom"),
                ],
                db_index=True,
                help_text="Market region (canonical values only)",
                max_length=32,
                null=True,
                blank=True,
            ),
        ),
    ]
