from django.db import migrations


FORWARD_SQL = r"""
DO $$
DECLARE
    col_list TEXT := 'id, session_number, year, month, date, day, captured_at, country, future, '
        || 'country_future, weight, bhs, wndw, '
        || 'country_future_wndw_total, strong_buy_worked, strong_buy_worked_percentage, '
        || 'strong_buy_didnt_work, strong_buy_didnt_work_percentage, buy_worked, buy_worked_percentage, '
        || 'buy_didnt_work, buy_didnt_work_percentage, hold, hold_percentage, '
        || 'strong_sell_worked, strong_sell_worked_percentage, strong_sell_didnt_work, strong_sell_didnt_work_percentage, '
        || 'sell_worked, sell_worked_percentage, sell_didnt_work, sell_didnt_work_percentage, '
        || 'session_bid, bid_size, last_price, session_ask, ask_size, '
        || 'entry_price, target_high, target_low, '
        || 'volume, change, change_percent, vwap, spread, '
        || 'session_close, session_open, open_vs_prev_number, open_vs_prev_percent, '
        || 'day_24h_low, day_24h_high, range_high_low, range_percent, '
        || 'week_52_low, week_52_high, week_52_range_high_low, week_52_range_percent, '
        || 'weighted_average, instrument_count, created_at, updated_at';
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'FutureTrading_marketsession'
          AND table_schema = 'public'
    ) THEN
        RAISE NOTICE 'FutureTrading_marketsession missing; skipping reorder';
        RETURN;
    END IF;

    EXECUTE 'DROP TABLE IF EXISTS "FutureTrading_marketsession_tmp" CASCADE';

    CREATE TABLE "FutureTrading_marketsession_tmp" (
        id SERIAL PRIMARY KEY,
        session_number integer NOT NULL,
        year integer NOT NULL,
        month integer NOT NULL,
        date integer NOT NULL,
        day varchar(10) NOT NULL,
        captured_at timestamp with time zone NOT NULL,
        country varchar(50) NOT NULL,
        future varchar(10),
        country_future numeric(14,4),
        weight integer,
        bhs varchar(20) NOT NULL,
        wndw varchar(20) DEFAULT 'PENDING',
        country_future_wndw_total numeric(14,4),
        strong_buy_worked numeric(14,4),
        strong_buy_worked_percentage numeric(14,4),
        strong_buy_didnt_work numeric(14,4),
        strong_buy_didnt_work_percentage numeric(14,4),
        buy_worked numeric(14,4),
        buy_worked_percentage numeric(14,4),
        buy_didnt_work numeric(14,4),
        buy_didnt_work_percentage numeric(14,4),
        hold numeric(14,4),
        hold_percentage numeric(14,4),
        strong_sell_worked numeric(14,4),
        strong_sell_worked_percentage numeric(14,4),
        strong_sell_didnt_work numeric(14,4),
        strong_sell_didnt_work_percentage numeric(14,4),
        sell_worked numeric(14,4),
        sell_worked_percentage numeric(14,4),
        sell_didnt_work numeric(14,4),
        sell_didnt_work_percentage numeric(14,4),
        session_bid numeric(14,4),
        bid_size integer,
        last_price numeric(14,4),
        session_ask numeric(14,4),
        ask_size integer,
        entry_price numeric(14,4),
        target_high numeric(14,4),
        target_low numeric(14,4),
        volume bigint,
        change numeric(14,4),
        change_percent numeric(14,6),
        vwap numeric(14,4),
        spread numeric(14,4),
        session_close numeric(14,4),
        session_open numeric(14,4),
        open_vs_prev_number numeric(14,4),
        open_vs_prev_percent numeric(14,4),
        day_24h_low numeric(14,4),
        day_24h_high numeric(14,4),
        range_high_low numeric(14,4),
        range_percent numeric(14,6),
        week_52_low numeric(14,4),
        week_52_high numeric(14,4),
        week_52_range_high_low numeric(14,4),
        week_52_range_percent numeric(14,6),
        weighted_average numeric(14,6),
        instrument_count integer DEFAULT 11,
        created_at timestamp with time zone NOT NULL,
        updated_at timestamp with time zone NOT NULL,
        CONSTRAINT ft_msession_tmp_unique UNIQUE (country, year, month, date, future)
    );

    EXECUTE format(
        'INSERT INTO "FutureTrading_marketsession_tmp" (%s) SELECT %s FROM "FutureTrading_marketsession"',
        col_list,
        col_list
    );

    DROP TABLE "FutureTrading_marketsession";
    ALTER TABLE "FutureTrading_marketsession_tmp" RENAME TO "FutureTrading_marketsession";
    ALTER INDEX ft_msession_tmp_unique RENAME TO FutureTrading_marketsession_country_year_month_date_future_e20093d3_uniq;

    PERFORM setval(
        pg_get_serial_sequence('"FutureTrading_marketsession"', 'id'),
        COALESCE((SELECT MAX(id) FROM "FutureTrading_marketsession"), 1),
        true
    );
END$$;
"""

REVERSE_SQL = "SELECT 1;"


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0048_set_target_offsets"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
