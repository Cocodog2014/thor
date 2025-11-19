from django.db import migrations

# NOTE: PostgreSQL does not support true column reordering; this migration
# recreates the table with the desired logical ordering placing `bhs` directly
# after `future`. Data is copied losslessly. Large tables may lock during swap.
# Consider running in a maintenance window if table is big.

FORWARD_SQL = r"""
BEGIN;
CREATE TABLE futuretrading_marketsession_new (
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
    open_vs_prev_number numeric(10,2),
    open_vs_prev_percent numeric(10,4),
    reference_last numeric(10,2),
    last_price numeric(10,2),
    change numeric(10,2),
    change_percent numeric(10,4),
    reference_ask numeric(10,2),
    ask_size integer,
    reference_bid numeric(10,2),
    bid_size integer,
    volume bigint,
    vwap numeric(10,2),
    spread numeric(10,2),
    day_24h_low numeric(10,2),
    day_24h_high numeric(10,2),
    range_high_low numeric(10,2),
    range_percent numeric(10,4),
    week_52_low numeric(10,2),
    week_52_high numeric(10,2),
    week_52_range_high_low numeric(10,2),
    week_52_range_percent numeric(10,4),
    entry_price numeric(10,2),
    target_high numeric(10,2),
    target_low numeric(10,2),
    weighted_average numeric(10,4),
    weight integer,
    sum_weighted numeric(10,2),
    instrument_count integer,
    status varchar(50) NOT NULL,
    strong_sell_flag boolean NOT NULL,
    study_fw varchar(50) NOT NULL,
    fw_weight numeric(10,4),
    outcome varchar(20) NOT NULL,
    didnt_work boolean NOT NULL,
    fw_nwdw varchar(20) NOT NULL,
    exit_price numeric(10,2),
    exit_time timestamp with time zone,
    fw_exit_value numeric(10,2),
    fw_exit_percent numeric(10,4),
    fw_stopped_out_value numeric(10,2),
    fw_stopped_out_nwdw varchar(20),
    close_last_price numeric(10,2),
    close_change numeric(10,2),
    close_change_percent numeric(10,4),
    close_bid numeric(10,2),
    close_bid_size integer,
    close_ask numeric(10,2),
    close_ask_size integer,
    close_volume bigint,
    close_vwap numeric(10,2),
    close_spread numeric(10,2),
    close_captured_at timestamp with time zone,
    close_weighted_average numeric(10,4),
    close_signal varchar(20),
    close_weight integer,
    close_sum_weighted numeric(10,2),
    close_instrument_count integer,
    close_status varchar(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT futuretrading_marketsession_new_uniq UNIQUE (country, year, month, date, future)
);

INSERT INTO futuretrading_marketsession_new (
    id, session_number, year, month, date, day, captured_at, country, future, bhs,
    reference_open, reference_close, open_vs_prev_number, open_vs_prev_percent, reference_last,
    last_price, change, change_percent, reference_ask, ask_size, reference_bid, bid_size, volume,
    vwap, spread, day_24h_low, day_24h_high, range_high_low, range_percent, week_52_low, week_52_high,
    week_52_range_high_low, week_52_range_percent, entry_price, target_high, target_low,
    weighted_average, weight, sum_weighted, instrument_count, status, strong_sell_flag, study_fw, fw_weight,
    outcome, didnt_work, fw_nwdw, exit_price, exit_time, fw_exit_value, fw_exit_percent,
    fw_stopped_out_value, fw_stopped_out_nwdw, close_last_price, close_change, close_change_percent,
    close_bid, close_bid_size, close_ask, close_ask_size, close_volume, close_vwap, close_spread,
    close_captured_at, close_weighted_average, close_signal, close_weight, close_sum_weighted, close_instrument_count,
    close_status, created_at, updated_at
)
SELECT
    id, session_number, year, month, date, day, captured_at, country, future, bhs,
    reference_open, reference_close, open_vs_prev_number, open_vs_prev_percent, reference_last,
    last_price, change, change_percent, reference_ask, ask_size, reference_bid, bid_size, volume,
    vwap, spread, day_24h_low, day_24h_high, range_high_low, range_percent, week_52_low, week_52_high,
    week_52_range_high_low, week_52_range_percent, entry_price, target_high, target_low,
    weighted_average, weight, sum_weighted, instrument_count, status, strong_sell_flag, study_fw, fw_weight,
    outcome, didnt_work, fw_nwdw, exit_price, exit_time, fw_exit_value, fw_exit_percent,
    fw_stopped_out_value, fw_stopped_out_nwdw, close_last_price, close_change, close_change_percent,
    close_bid, close_bid_size, close_ask, close_ask_size, close_volume, close_vwap, close_spread,
    close_captured_at, close_weighted_average, close_signal, close_weight, close_sum_weighted, close_instrument_count,
    close_status, created_at, updated_at
FROM futuretrading_marketsession;

DROP TABLE futuretrading_marketsession;
ALTER TABLE futuretrading_marketsession_new RENAME TO futuretrading_marketsession;
COMMIT;
"""

# Reverse simply leaves ordering as-is (no reconstruction of old order)
REVERSE_SQL = """-- Irreversible column reorder; no-op on downgrade."""

class Migration(migrations.Migration):
    dependencies = [
        ("FutureTrading", "0017_rename_total_signal_to_bhs"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
