from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Instruments", "0022_watchlist_mode_column_rename"),
    ]

    operations = [
        # Convert any legacy GLOBAL rows into LIVE so the system only has paper/live going forward.
        migrations.RunSQL(
            sql=(
                'UPDATE "Instruments_userinstrumentwatchlistitem" '
                'SET "trading_mode" = \'LIVE\' '
                'WHERE "trading_mode" = \'GLOBAL\';'
            ),
            reverse_sql=(
                'UPDATE "Instruments_userinstrumentwatchlistitem" '
                'SET "trading_mode" = \'GLOBAL\' '
                'WHERE "trading_mode" = \'LIVE\' AND "user_id" = 1;'
            ),
        ),
    ]
