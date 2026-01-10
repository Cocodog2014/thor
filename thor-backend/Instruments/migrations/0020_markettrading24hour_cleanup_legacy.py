from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Instruments", "0019_markettrading24hour_rename_session_group_column"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
DO $$
BEGIN
    -- If any legacy table survived (owned by ThorTrading), remove it.
    IF to_regclass('public."ThorTrading_markettrading24hour"') IS NOT NULL THEN
        IF to_regclass('public."Instruments_markettrading24hour"') IS NULL THEN
            ALTER TABLE public."ThorTrading_markettrading24hour" RENAME TO "Instruments_markettrading24hour";
        ELSE
            DROP TABLE public."ThorTrading_markettrading24hour";
        END IF;
    END IF;
END $$;

-- Ensure expected index exists
CREATE INDEX IF NOT EXISTS idx_mkt24h_date_sym
    ON public."Instruments_markettrading24hour" (session_date, symbol);

-- Ensure a UNIQUE constraint exists on (session_number, symbol)
DO $$
DECLARE
    has_uq BOOLEAN;
BEGIN
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
          ) = ARRAY['session_number','symbol']
    ) INTO has_uq;

    IF NOT has_uq THEN
        EXECUTE 'ALTER TABLE public."Instruments_markettrading24hour" '
                'ADD CONSTRAINT uq_mkt24h_session_sym UNIQUE (session_number, symbol)';
    END IF;
END $$;
""",
            reverse_sql=migrations.RunSQL.noop,
        )
    ]
