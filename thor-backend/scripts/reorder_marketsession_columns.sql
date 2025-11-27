-- Script to reorder FutureTrading_marketsession columns
-- Moves target_hit_* columns to appear after entry_price

BEGIN;

-- Create new table with desired column order
CREATE TABLE "FutureTrading_marketsession_new" (
    "id" serial NOT NULL PRIMARY KEY,
    "session_number" integer NOT NULL,
    "capture_group" integer,
    "year" integer NOT NULL,
    "month" integer NOT NULL,
    "date" integer NOT NULL,
    "day" varchar(10) NOT NULL,
    "captured_at" timestamp with time zone NOT NULL,
    "country" varchar(50) NOT NULL,
    "future" varchar(10),
    "country_future" numeric(14, 4),
    "weight" integer,
    "bhs" varchar(20) NOT NULL,
    "wndw" varchar(20),
    "country_future_wndw_total" bigint,
    "bid_price" numeric(14, 4),
    "bid_size" integer,
    "last_price" numeric(14, 4),
    "spread" numeric(14, 4),
    "ask_price" numeric(14, 4),
    "ask_size" integer,
    "entry_price" numeric(14, 4),
    "target_hit_price" numeric(14, 4),
    "target_hit_type" varchar(10),
    "target_high" numeric(14, 4),
    "target_low" numeric(14, 4),
    "target_hit_at" timestamp with time zone,
    "volume" bigint,
    "vwap" numeric(14, 4),
    "market_open" numeric(14, 4),
    "market_high_open" numeric(14, 4),
    "market_high_pct_open" numeric(14, 6),
    "market_low_open" numeric(14, 4),
    "market_low_pct_open" numeric(14, 6),
    "market_close" numeric(14, 4),
    "market_high_pct_close" numeric(14, 4),
    "market_low_pct_close" numeric(14, 4),
    "market_close_vs_open_pct" numeric(14, 4),
    "market_range" numeric(14, 4),
    "market_range_pct" numeric(14, 6),
    "prev_close_24h" numeric(14, 4),
    "open_price_24h" numeric(14, 4),
    "open_prev_diff_24h" numeric(14, 4),
    "open_prev_pct_24h" numeric(14, 4),
    "low_24h" numeric(14, 4),
    "high_24h" numeric(14, 4),
    "range_diff_24h" numeric(14, 4),
    "range_pct_24h" numeric(14, 6),
    "low_52w" numeric(14, 4),
    "low_pct_52w" numeric(14, 4),
    "high_52w" numeric(14, 4),
    "high_pct_52w" numeric(14, 4),
    "range_52w" numeric(14, 4),
    "range_pct_52w" numeric(14, 6),
    "weighted_average" numeric(14, 6),
    "instrument_count" integer,
    "strong_buy_worked" numeric(14, 4),
    "strong_buy_worked_percentage" numeric(14, 4),
    "strong_buy_didnt_work" numeric(14, 4),
    "strong_buy_didnt_work_percentage" numeric(14, 4),
    "buy_worked" numeric(14, 4),
    "buy_worked_percentage" numeric(14, 4),
    "buy_didnt_work" numeric(14, 4),
    "buy_didnt_work_percentage" numeric(14, 4),
    "hold" numeric(14, 4),
    "strong_sell_worked" numeric(14, 4),
    "strong_sell_worked_percentage" numeric(14, 4),
    "strong_sell_didnt_work" numeric(14, 4),
    "strong_sell_didnt_work_percentage" numeric(14, 4),
    "sell_worked" numeric(14, 4),
    "sell_worked_percentage" numeric(14, 4),
    "sell_didnt_work" numeric(14, 4),
    "sell_didnt_work_percentage" numeric(14, 4)
);

-- Copy data from old table to new table
INSERT INTO "FutureTrading_marketsession_new" 
SELECT 
    id, session_number, capture_group, year, month, date, day, captured_at,
    country, future, country_future, weight, bhs, wndw, country_future_wndw_total,
    bid_price, bid_size, last_price, spread, ask_price, ask_size,
    entry_price, target_hit_price, target_hit_type, target_high, target_low, target_hit_at,
    volume, vwap, market_open, market_high_open, market_high_pct_open,
    market_low_open, market_low_pct_open, market_close,
    market_high_pct_close, market_low_pct_close, market_close_vs_open_pct,
    market_range, market_range_pct, prev_close_24h, open_price_24h,
    open_prev_diff_24h, open_prev_pct_24h, low_24h, high_24h,
    range_diff_24h, range_pct_24h, low_52w, low_pct_52w, high_52w, high_pct_52w,
    range_52w, range_pct_52w, weighted_average, instrument_count,
    strong_buy_worked, strong_buy_worked_percentage, strong_buy_didnt_work, strong_buy_didnt_work_percentage,
    buy_worked, buy_worked_percentage, buy_didnt_work, buy_didnt_work_percentage,
    hold, strong_sell_worked, strong_sell_worked_percentage,
    strong_sell_didnt_work, strong_sell_didnt_work_percentage, sell_worked, sell_worked_percentage,
    sell_didnt_work, sell_didnt_work_percentage
FROM "FutureTrading_marketsession";

-- Drop old table
DROP TABLE "FutureTrading_marketsession";

-- Rename new table to original name
ALTER TABLE "FutureTrading_marketsession_new" RENAME TO "FutureTrading_marketsession";

-- Recreate indexes
CREATE INDEX "FutureTrading_marke_capture_group_ef5816_idx" ON "FutureTrading_marketsession" ("capture_group");
CREATE INDEX "FutureTrading_marketsession_country_idx" ON "FutureTrading_marketsession" ("country");
CREATE INDEX "FutureTrading_marketsession_future_idx" ON "FutureTrading_marketsession" ("future");
CREATE INDEX "FutureTrading_marketsession_session_number_idx" ON "FutureTrading_marketsession" ("session_number");
CREATE INDEX "FutureTrading_marketsession_captured_at_idx" ON "FutureTrading_marketsession" ("captured_at");
CREATE INDEX "FutureTrading_marketsession_bhs_idx" ON "FutureTrading_marketsession" ("bhs");
CREATE INDEX "FutureTrading_marketsession_wndw_idx" ON "FutureTrading_marketsession" ("wndw");

-- Reset sequence
SELECT setval(pg_get_serial_sequence('"FutureTrading_marketsession"', 'id'), 
              GREATEST(1, COALESCE((SELECT MAX(id) FROM "FutureTrading_marketsession"), 0)), 
              true);

COMMIT;

-- Verify column order
SELECT column_name, ordinal_position, data_type 
FROM information_schema.columns 
WHERE table_name = 'FutureTrading_marketsession' 
ORDER BY ordinal_position;
