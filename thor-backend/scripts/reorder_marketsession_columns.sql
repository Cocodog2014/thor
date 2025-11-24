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
    "country_future_wndw_total" numeric(14, 4),
    "bid_price" numeric(14, 4),
    "bid_size" integer,
    "last_price" numeric(14, 4),
    "spread" numeric(14, 4),
    "ask_price" numeric(14, 4),
    "ask_size" integer,
    "entry_price" numeric(14, 4),
    "target_hit_price" numeric(14, 4),
    "target_hit_at" timestamp with time zone,
    "target_hit_type" varchar(10),
    "target_high" numeric(14, 4),
    "target_low" numeric(14, 4),
    "volume" bigint,
    "vwap" numeric(14, 4),
    "market_open" numeric(14, 4),
    "market_high_number" numeric(14, 4),
    "market_high_percentage" numeric(14, 6),
    "market_low_number" numeric(14, 4),
    "market_low_percentage" numeric(14, 6),
    "market_close_number" numeric(14, 4),
    "market_close_percentage" numeric(14, 6),
    "market_range_number" numeric(14, 4),
    "market_range_percentage" numeric(14, 6),
    "session_close" numeric(14, 4),
    "session_open" numeric(14, 4),
    "open_vs_prev_number" numeric(14, 4),
    "open_vs_prev_percent" numeric(14, 4),
    "day_24h_low" numeric(14, 4),
    "day_24h_high" numeric(14, 4),
    "range_high_low" numeric(14, 4),
    "range_percent" numeric(14, 6),
    "week_52_low" numeric(14, 4),
    "week_52_high" numeric(14, 4),
    "week_52_range_high_low" numeric(14, 4),
    "week_52_range_percent" numeric(14, 6),
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
    "hold_percentage" numeric(14, 4),
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
    entry_price, target_hit_price, target_hit_at, target_hit_type, target_high, target_low,
    volume, vwap, market_open, market_high_number, market_high_percentage,
    market_low_number, market_low_percentage, market_close_number, market_close_percentage,
    market_range_number, market_range_percentage, session_close, session_open,
    open_vs_prev_number, open_vs_prev_percent, day_24h_low, day_24h_high,
    range_high_low, range_percent, week_52_low, week_52_high,
    week_52_range_high_low, week_52_range_percent, weighted_average, instrument_count,
    strong_buy_worked, strong_buy_worked_percentage, strong_buy_didnt_work, strong_buy_didnt_work_percentage,
    buy_worked, buy_worked_percentage, buy_didnt_work, buy_didnt_work_percentage,
    hold, hold_percentage, strong_sell_worked, strong_sell_worked_percentage,
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
              COALESCE((SELECT MAX(id) FROM "FutureTrading_marketsession"), 1), 
              true);

COMMIT;

-- Verify column order
SELECT column_name, ordinal_position, data_type 
FROM information_schema.columns 
WHERE table_name = 'FutureTrading_marketsession' 
ORDER BY ordinal_position;
