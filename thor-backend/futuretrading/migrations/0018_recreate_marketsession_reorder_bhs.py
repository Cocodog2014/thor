from django.db import migrations

FORWARD_SQL = r"""
DO $$
DECLARE
    tbl TEXT := 'FutureTrading_marketsession';
    col_list TEXT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = tbl AND table_schema = 'public'
    ) THEN
        RAISE EXCEPTION 'Table % does not exist; abort reorder', tbl;
    END IF;

    -- Create new table with reordered columns (bhs directly after future)
    CREATE TABLE "FutureTrading_marketsession_new" (
        id SERIAL PRIMARY KEY,
        session_number integer NOT NULL,
        year integer NOT NULL,
        month integer NOT NULL,
        date integer NOT NULL,
        day varchar(10) NOT NULL,
        captured_at timestamp with time zone NOT NULL,
        country varchar(50) NOT NULL,
        future varchar(10),
        bhs varchar(20) NOT NULL,
        reference_open numeric(10,2),
        reference_close numeric(10,2),
        reference_ask numeric(10,2),
        reference_bid numeric(10,2),
        reference_last numeric(10,2),
        entry_price numeric(10,2),
        target_high numeric(10,2),
        target_low numeric(10,2),
        strong_sell_flag boolean NOT NULL,
        study_fw varchar(50) NOT NULL,
        fw_weight numeric(10,4),
        didnt_work boolean NOT NULL,
        fw_nwdw varchar(20) NOT NULL,
        fw_exit_value numeric(10,2),
        fw_exit_percent numeric(10,4),
        fw_stopped_out_value numeric(10,2),
        fw_stopped_out_nwdw varchar(20) NOT NULL,
        created_at timestamp with time zone NOT NULL,
        updated_at timestamp with time zone NOT NULL,
        ask_size integer,
        bid_size integer,
        change numeric(10,2),
        change_percent numeric(10,4),
        close_ask numeric(10,2),
        close_ask_size integer,
        close_bid numeric(10,2),
        close_bid_size integer,
        close_captured_at timestamp with time zone,
        close_change numeric(10,2),
        close_change_percent numeric(10,4),
        close_instrument_count integer,
        close_last_price numeric(10,2),
        close_signal varchar(20) NOT NULL,
        close_spread numeric(10,2),
        close_status varchar(50) NOT NULL,
        close_sum_weighted numeric(10,2),
        close_volume bigint,
        close_vwap numeric(10,2),
        close_weight integer,
        close_weighted_average numeric(10,4),
        day_24h_high numeric(10,2),
        day_24h_low numeric(10,2),
        exit_price numeric(10,2),
        exit_time timestamp with time zone,
        instrument_count integer,
        last_price numeric(10,2),
        open_vs_prev_number numeric(10,2),
        open_vs_prev_percent numeric(10,4),
        outcome varchar(20) NOT NULL,
        range_high_low numeric(10,2),
        range_percent numeric(10,4),
        spread numeric(10,2),
        status varchar(50) NOT NULL,
        sum_weighted numeric(10,2),
        volume bigint,
        vwap numeric(10,2),
        week_52_high numeric(10,2),
        week_52_low numeric(10,2),
        week_52_range_high_low numeric(10,2),
        week_52_range_percent numeric(10,4),
        weight integer,
        weighted_average numeric(10,4),
        CONSTRAINT futuretrading_marketsession_new_uniq UNIQUE (country, year, month, date, future)
    );

    col_list := 'id, session_number, year, month, date, day, captured_at, country, future, bhs, '
        || 'reference_open, reference_close, reference_ask, reference_bid, reference_last, '
        || 'entry_price, target_high, target_low, strong_sell_flag, study_fw, fw_weight, didnt_work, fw_nwdw, '
        || 'fw_exit_value, fw_exit_percent, fw_stopped_out_value, fw_stopped_out_nwdw, created_at, updated_at, '
        || 'ask_size, bid_size, change, change_percent, close_ask, close_ask_size, close_bid, close_bid_size, '
        || 'close_captured_at, close_change, close_change_percent, close_instrument_count, close_last_price, close_signal, close_spread, close_status, '
        || 'close_sum_weighted, close_volume, close_vwap, close_weight, close_weighted_average, day_24h_high, day_24h_low, '
        || 'exit_price, exit_time, instrument_count, last_price, open_vs_prev_number, open_vs_prev_percent, outcome, '
        || 'range_high_low, range_percent, spread, status, sum_weighted, volume, vwap, '
        || 'week_52_high, week_52_low, week_52_range_high_low, week_52_range_percent, weight, weighted_average';

    EXECUTE format(
        'INSERT INTO "FutureTrading_marketsession_new" (%s) SELECT %s FROM %I',
        col_list,
        col_list,
        tbl
    );

    -- Drop old table and rename new
    EXECUTE format('DROP TABLE %I', tbl);
    ALTER TABLE "FutureTrading_marketsession_new" RENAME TO "FutureTrading_marketsession";

    -- Reset sequence value
    PERFORM setval(
        pg_get_serial_sequence('"FutureTrading_marketsession"','id'),
        GREATEST(1, COALESCE((SELECT MAX(id) FROM "FutureTrading_marketsession"), 0))
    );
END$$;
"""

REVERSE_SQL = """-- Irreversible rebuild."""

class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0017_rename_total_signal_to_bhs"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
