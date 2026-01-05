from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0007_instrumentintraday_rolling52weekstats"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # State: the model is now managed and lives under the Instruments_* table.
            state_operations=[
                migrations.AlterModelOptions(
                    name="rolling52weekstats",
                    options={
                        "verbose_name": "52-Week Stats",
                        "verbose_name_plural": "52-Week Stats",
                        "ordering": ["symbol"],
                        "managed": True,
                    },
                ),
                migrations.AlterModelTable(
                    name="rolling52weekstats",
                    table="Instruments_rolling52weekstats",
                ),
            ],
            # DB: drop the legacy/test table if present, then create the new one.
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS "ThorTrading_rolling52weekstats" CASCADE;',
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql='''
CREATE TABLE IF NOT EXISTS "Instruments_rolling52weekstats" (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL UNIQUE,
    high_52w NUMERIC(14, 4) NOT NULL,
    high_52w_date DATE NOT NULL,
    low_52w NUMERIC(14, 4) NOT NULL,
    low_52w_date DATE NOT NULL,
    last_price_checked NUMERIC(14, 4) NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    all_time_high NUMERIC(14, 4) NULL,
    all_time_high_date DATE NULL,
    all_time_low NUMERIC(14, 4) NULL,
    all_time_low_date DATE NULL
);

CREATE INDEX IF NOT EXISTS instruments_rolling52weekstats_symbol_idx
    ON "Instruments_rolling52weekstats" (symbol);
''',
                    reverse_sql='DROP TABLE IF EXISTS "Instruments_rolling52weekstats" CASCADE;',
                ),
            ],
        ),
    ]
