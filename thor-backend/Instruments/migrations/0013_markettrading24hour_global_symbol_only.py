from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Instruments", "0012_delete_tradinginstrument"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelOptions(
                    name="markettrading24hour",
                    options={
                        "managed": True,
                        "verbose_name": "24-Hour Stats",
                        "verbose_name_plural": "24-Hour Stats",
                        "unique_together": {("session_group", "symbol")},
                        "indexes": [
                            models.Index(
                                fields=["session_date", "symbol"],
                                name="idx_mkt24h_date_sym",
                            )
                        ],
                    },
                ),
                migrations.RemoveField(
                    model_name="markettrading24hour",
                    name="country",
                ),
                migrations.AlterUniqueTogether(
                    name="markettrading24hour",
                    unique_together={("session_group", "symbol")},
                ),
                migrations.RemoveIndex(
                    model_name="markettrading24hour",
                    name="idx_mkt24h_date_cty_sym",
                ),
                migrations.AddIndex(
                    model_name="markettrading24hour",
                    index=models.Index(
                        fields=["session_date", "symbol"],
                        name="idx_mkt24h_date_sym",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=r"""
DO $$
BEGIN
    -- Fresh installs / test DBs may not have this legacy-owned table yet.
    -- Create a minimal version so subsequent ALTER/DROP statements succeed.
    IF to_regclass('public."Instruments_markettrading24hour"') IS NULL THEN
        CREATE TABLE public."Instruments_markettrading24hour" (
            id BIGSERIAL PRIMARY KEY,
            session_group INTEGER NOT NULL,
            session_date DATE NOT NULL,
            country VARCHAR(32),
            symbol VARCHAR(32) NOT NULL,
            prev_close_24h NUMERIC(14, 4) NULL,
            open_price_24h NUMERIC(14, 4) NULL,
            open_prev_diff_24h NUMERIC(14, 4) NULL,
            open_prev_pct_24h NUMERIC(14, 4) NULL,
            low_24h NUMERIC(14, 4) NULL,
            high_24h NUMERIC(14, 4) NULL,
            range_diff_24h NUMERIC(14, 4) NULL,
            range_pct_24h NUMERIC(14, 4) NULL,
            close_24h NUMERIC(14, 4) NULL,
            volume_24h BIGINT NULL,
            finalized BOOLEAN NOT NULL DEFAULT FALSE
        );
    END IF;
END $$;

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop any UNIQUE constraint that involves the (now-removed) country column.
    FOR r IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'Instruments_markettrading24hour'
          AND con.contype = 'u'
          AND EXISTS (
              SELECT 1
              FROM unnest(con.conkey) AS u(attnum)
              JOIN pg_attribute a ON a.attrelid = rel.oid AND a.attnum = u.attnum
              WHERE a.attname = 'country'
          )
    LOOP
        EXECUTE format('ALTER TABLE public."Instruments_markettrading24hour" DROP CONSTRAINT IF EXISTS %I', r.conname);
    END LOOP;
END $$;

DROP INDEX IF EXISTS public.idx_mkt24h_date_cty_sym;

ALTER TABLE public."Instruments_markettrading24hour"
    DROP COLUMN IF EXISTS "country";

DO $$
DECLARE
    has_uq BOOLEAN;
BEGIN
    -- Ensure a UNIQUE constraint exists on (session_group, symbol).
    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'Instruments_markettrading24hour'
          AND con.contype = 'u'
          AND (
              SELECT array_agg(a.attname::text ORDER BY a.attname::text)
              FROM unnest(con.conkey) AS u(attnum)
              JOIN pg_attribute a ON a.attrelid = rel.oid AND a.attnum = u.attnum
          ) = ARRAY['session_group','symbol']
    ) INTO has_uq;

    IF NOT has_uq THEN
        EXECUTE 'ALTER TABLE public."Instruments_markettrading24hour" '
                'ADD CONSTRAINT uq_mkt24h_group_sym UNIQUE (session_group, symbol)';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_mkt24h_date_sym
    ON public."Instruments_markettrading24hour" (session_date, symbol);
""",
                    reverse_sql=r"""
DROP INDEX IF EXISTS public.idx_mkt24h_date_sym;

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop the unique constraint we may have created.
    IF EXISTS (
        SELECT 1
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'Instruments_markettrading24hour'
          AND con.contype = 'u'
          AND con.conname = 'uq_mkt24h_group_sym'
    ) THEN
        EXECUTE 'ALTER TABLE public."Instruments_markettrading24hour" DROP CONSTRAINT uq_mkt24h_group_sym';
    END IF;
END $$;

ALTER TABLE public."Instruments_markettrading24hour"
    ADD COLUMN IF NOT EXISTS "country" varchar(32);

CREATE INDEX IF NOT EXISTS idx_mkt24h_date_cty_sym
    ON public."Instruments_markettrading24hour" (session_date, country, symbol);
""",
                )
            ],
        )
    ]
