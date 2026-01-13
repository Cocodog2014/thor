from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Instruments", "0021_watchlist_modes"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "Instruments_userinstrumentwatchlistitem" RENAME COLUMN "mode" TO "trading_mode";',
                    reverse_sql='ALTER TABLE "Instruments_userinstrumentwatchlistitem" RENAME COLUMN "trading_mode" TO "mode";',
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="userinstrumentwatchlistitem",
                    name="mode",
                    field=models.CharField(
                        choices=[("GLOBAL", "Global"), ("PAPER", "Paper"), ("LIVE", "Live")],
                        db_column="trading_mode",
                        db_index=True,
                        default="LIVE",
                        help_text="Watchlist scope/mode: GLOBAL (admin), PAPER, or LIVE.",
                        max_length=10,
                    ),
                ),
            ],
        ),
    ]
