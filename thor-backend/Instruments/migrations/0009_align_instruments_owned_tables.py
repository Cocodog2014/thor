from __future__ import annotations

from django.db import migrations, models


def _rename_or_create_sql() -> str:
    # Postgres helper: rename legacy table if present; otherwise create the new table.
    # All data is test-only, but renaming preserves data when available.
    return r'''
-- Rename legacy tables owned by Instruments (if present).
DO $$
BEGIN
    IF to_regclass('public."ThorTrading_instrumentintraday"') IS NOT NULL
       AND to_regclass('public."Instruments_instrumentintraday"') IS NULL THEN
        ALTER TABLE "ThorTrading_instrumentintraday" RENAME TO "Instruments_instrumentintraday";
    END IF;
    IF to_regclass('public."ThorTrading_markettrading24hour"') IS NOT NULL
       AND to_regclass('public."Instruments_markettrading24hour"') IS NULL THEN
        ALTER TABLE "ThorTrading_markettrading24hour" RENAME TO "Instruments_markettrading24hour";
    END IF;
END $$;

-- RTD tables (previously state-only)
DO $$
BEGIN
    IF to_regclass('public."ThorTrading_instrumentcategory"') IS NOT NULL
       AND to_regclass('public."Instruments_instrumentcategory"') IS NULL THEN
        ALTER TABLE "ThorTrading_instrumentcategory" RENAME TO "Instruments_instrumentcategory";
    END IF;

    IF to_regclass('public."Instruments_instrumentcategory"') IS NULL THEN
        CREATE TABLE "Instruments_instrumentcategory" (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            display_name VARCHAR(100) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            color_primary VARCHAR(7) NOT NULL DEFAULT '#4CAF50',
            color_secondary VARCHAR(7) NOT NULL DEFAULT '#81C784',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public."ThorTrading_tradinginstrument"') IS NOT NULL
       AND to_regclass('public."Instruments_tradinginstrument"') IS NULL THEN
        ALTER TABLE "ThorTrading_tradinginstrument" RENAME TO "Instruments_tradinginstrument";
    END IF;

    IF to_regclass('public."Instruments_tradinginstrument"') IS NULL THEN
        CREATE TABLE "Instruments_tradinginstrument" (
            id BIGSERIAL PRIMARY KEY,
            country VARCHAR(32) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            category_id BIGINT NOT NULL REFERENCES "Instruments_instrumentcategory"(id) ON DELETE CASCADE,
            exchange VARCHAR(50) NOT NULL DEFAULT '',
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_watchlist BOOLEAN NOT NULL DEFAULT FALSE,
            show_in_ribbon BOOLEAN NOT NULL DEFAULT FALSE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            display_precision INTEGER NOT NULL DEFAULT 2,
            tick_size NUMERIC(10, 6) NULL,
            contract_size NUMERIC(15, 2) NULL,
            tick_value NUMERIC(10, 2) NULL,
            margin_requirement NUMERIC(15, 2) NULL,
            api_provider VARCHAR(50) NOT NULL DEFAULT '',
            api_symbol VARCHAR(100) NOT NULL DEFAULT '',
            feed_symbol VARCHAR(100) NOT NULL DEFAULT '',
            update_frequency INTEGER NOT NULL DEFAULT 5,
            last_updated TIMESTAMPTZ NULL,
            is_market_open BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uniq_instr_country_symbol UNIQUE (country, symbol)
        );
        CREATE INDEX idx_instr_country_symbol ON "Instruments_tradinginstrument" (country, symbol);
        CREATE INDEX idx_instr_country_active ON "Instruments_tradinginstrument" (country, is_active);
        CREATE INDEX idx_instr_category_sort ON "Instruments_tradinginstrument" (category_id, sort_order);
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public."ThorTrading_signalweight"') IS NOT NULL
       AND to_regclass('public."Instruments_signalweight"') IS NULL THEN
        ALTER TABLE "ThorTrading_signalweight" RENAME TO "Instruments_signalweight";
    END IF;

    IF to_regclass('public."Instruments_signalweight"') IS NULL THEN
        CREATE TABLE "Instruments_signalweight" (
            id BIGSERIAL PRIMARY KEY,
            signal VARCHAR(20) NOT NULL UNIQUE,
            weight INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public."ThorTrading_signalstatvalue"') IS NOT NULL
       AND to_regclass('public."Instruments_signalstatvalue"') IS NULL THEN
        ALTER TABLE "ThorTrading_signalstatvalue" RENAME TO "Instruments_signalstatvalue";
    END IF;

    IF to_regclass('public."Instruments_signalstatvalue"') IS NULL THEN
        CREATE TABLE "Instruments_signalstatvalue" (
            id BIGSERIAL PRIMARY KEY,
            instrument_id BIGINT NOT NULL REFERENCES "Instruments_tradinginstrument"(id) ON DELETE CASCADE,
            signal VARCHAR(20) NOT NULL,
            value NUMERIC(10, 6) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uniq_signalstat_instrument_signal UNIQUE (instrument_id, signal)
        );
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public."ThorTrading_contractweight"') IS NOT NULL
       AND to_regclass('public."Instruments_contractweight"') IS NULL THEN
        ALTER TABLE "ThorTrading_contractweight" RENAME TO "Instruments_contractweight";
    END IF;

    IF to_regclass('public."Instruments_contractweight"') IS NULL THEN
        CREATE TABLE "Instruments_contractweight" (
            id BIGSERIAL PRIMARY KEY,
            instrument_id BIGINT NOT NULL UNIQUE REFERENCES "Instruments_tradinginstrument"(id) ON DELETE CASCADE,
            weight NUMERIC(8, 6) NOT NULL DEFAULT 1.0,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
    END IF;
END $$;
'''


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0008_instruments_rolling52weekstats_table"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelOptions(
                    name="instrumentintraday",
                    options={
                        "verbose_name": "Instrument Intraday Bar",
                        "verbose_name_plural": "Instrument Intraday Bars",
                        "managed": True,
                    },
                ),
                migrations.AlterModelTable(
                    name="instrumentintraday",
                    table="Instruments_instrumentintraday",
                ),
                migrations.AlterModelOptions(
                    name="markettrading24hour",
                    options={
                        "verbose_name": "24-Hour Global Session",
                        "verbose_name_plural": "24-Hour Global Sessions",
                        "managed": True,
                        "unique_together": {("session_group", "country", "symbol")},
                        "indexes": [models.Index(fields=["session_date", "country", "symbol"], name="idx_mkt24h_date_cty_sym")],
                    },
                ),
                migrations.AlterModelTable(
                    name="markettrading24hour",
                    table="Instruments_markettrading24hour",
                ),
                migrations.AlterModelOptions(
                    name="instrumentcategory",
                    options={
                        "ordering": ["sort_order", "name"],
                        "verbose_name": "Instrument Category",
                        "verbose_name_plural": "Instrument Categories",
                        "managed": True,
                    },
                ),
                migrations.AlterModelTable(
                    name="instrumentcategory",
                    table="Instruments_instrumentcategory",
                ),
                migrations.AlterModelOptions(
                    name="tradinginstrument",
                    options={
                        "ordering": ["sort_order", "country", "symbol"],
                        "verbose_name": "Trading Instrument",
                        "verbose_name_plural": "Trading Instruments",
                        "managed": True,
                        "indexes": [
                            models.Index(fields=["country", "symbol"], name="idx_instr_country_symbol"),
                            models.Index(fields=["country", "is_active"], name="idx_instr_country_active"),
                            models.Index(fields=["category", "sort_order"], name="idx_instr_category_sort"),
                        ],
                        "unique_together": {("country", "symbol")},
                    },
                ),
                migrations.AlterModelTable(
                    name="tradinginstrument",
                    table="Instruments_tradinginstrument",
                ),
                migrations.AlterModelOptions(
                    name="signalweight",
                    options={
                        "ordering": ["-weight"],
                        "verbose_name": "Signal Weight",
                        "verbose_name_plural": "Signal Weights",
                        "managed": True,
                    },
                ),
                migrations.AlterModelTable(
                    name="signalweight",
                    table="Instruments_signalweight",
                ),
                migrations.AlterModelOptions(
                    name="signalstatvalue",
                    options={
                        "ordering": ["instrument__country", "instrument__symbol", "signal"],
                        "verbose_name": "Signal Statistical Value",
                        "verbose_name_plural": "Signal Statistical Values",
                        "managed": True,
                        "unique_together": {("instrument", "signal")},
                    },
                ),
                migrations.AlterModelTable(
                    name="signalstatvalue",
                    table="Instruments_signalstatvalue",
                ),
                migrations.AlterModelOptions(
                    name="contractweight",
                    options={
                        "ordering": ["instrument__country", "instrument__symbol"],
                        "verbose_name": "Contract Weight",
                        "verbose_name_plural": "Contract Weights",
                        "managed": True,
                    },
                ),
                migrations.AlterModelTable(
                    name="contractweight",
                    table="Instruments_contractweight",
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=_rename_or_create_sql(),
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
        )
    ]
