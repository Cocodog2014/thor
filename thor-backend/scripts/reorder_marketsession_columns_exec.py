"""Reorder FutureTrading_marketsession to keep 52-week columns in desired order."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

import django  # noqa: E402
from django.db import connection, transaction  # noqa: E402

CREATE_TABLE_SQL = """
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
    "market_high_number" numeric(14, 4),
    "market_high_percentage" numeric(14, 6),
    "market_low_number" numeric(14, 4),
    "market_low_percentage" numeric(14, 6),
    "market_close_number" numeric(14, 4),
    "market_close_percentage_high" numeric(14, 4),
    "market_close_percentage_low" numeric(14, 4),
    "market_close_vs_open_percentage" numeric(14, 4),
    "market_range_number" numeric(14, 4),
    "market_range_percentage" numeric(14, 6),
    "prev_close_24h" numeric(14, 4),
    "open_price_24h" numeric(14, 4),
    "open_prev_diff_24h" numeric(14, 4),
    "open_prev_pct_24h" numeric(14, 4),
    "low_24h" numeric(14, 4),
    "high_24h" numeric(14, 4),
    "range_diff_24h" numeric(14, 4),
    "range_pct_24h" numeric(14, 6),
    "week_52_low" numeric(14, 4),
    "low_pct_52" numeric(14, 4),
    "week_52_high" numeric(14, 4),
    "high_pct_52" numeric(14, 4),
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
    "strong_sell_worked" numeric(14, 4),
    "strong_sell_worked_percentage" numeric(14, 4),
    "strong_sell_didnt_work" numeric(14, 4),
    "strong_sell_didnt_work_percentage" numeric(14, 4),
    "sell_worked" numeric(14, 4),
    "sell_worked_percentage" numeric(14, 4),
    "sell_didnt_work" numeric(14, 4),
    "sell_didnt_work_percentage" numeric(14, 4)
);
"""

INSERT_SQL = """
INSERT INTO "FutureTrading_marketsession_new"
SELECT
    id, session_number, capture_group, year, month, date, day, captured_at,
    country, future, country_future, weight, bhs, wndw, country_future_wndw_total,
    bid_price, bid_size, last_price, spread, ask_price, ask_size,
    entry_price, target_hit_price, target_hit_type, target_high, target_low, target_hit_at,
    volume, vwap, market_open, market_high_number, market_high_percentage,
    market_low_number, market_low_percentage, market_close_number,
    market_close_percentage_high, market_close_percentage_low, market_close_vs_open_percentage,
    market_range_number, market_range_percentage, prev_close_24h, open_price_24h,
    open_prev_diff_24h, open_prev_pct_24h, low_24h, high_24h,
    range_diff_24h, range_pct_24h, week_52_low, low_pct_52, week_52_high, high_pct_52,
    week_52_range_high_low, week_52_range_percent, weighted_average, instrument_count,
    strong_buy_worked, strong_buy_worked_percentage, strong_buy_didnt_work, strong_buy_didnt_work_percentage,
    buy_worked, buy_worked_percentage, buy_didnt_work, buy_didnt_work_percentage,
    hold, strong_sell_worked, strong_sell_worked_percentage,
    strong_sell_didnt_work, strong_sell_didnt_work_percentage, sell_worked, sell_worked_percentage,
    sell_didnt_work, sell_didnt_work_percentage
FROM "FutureTrading_marketsession";
"""

DROP_TABLE_SQL = 'DROP TABLE "FutureTrading_marketsession";'
RENAME_SQL = 'ALTER TABLE "FutureTrading_marketsession_new" RENAME TO "FutureTrading_marketsession";'

INDEX_SQL = [
    'CREATE INDEX "FutureTrading_marke_capture_group_ef5816_idx" ON "FutureTrading_marketsession" ("capture_group");',
    'CREATE INDEX "FutureTrading_marketsession_country_idx" ON "FutureTrading_marketsession" ("country");',
    'CREATE INDEX "FutureTrading_marketsession_future_idx" ON "FutureTrading_marketsession" ("future");',
    'CREATE INDEX "FutureTrading_marketsession_session_number_idx" ON "FutureTrading_marketsession" ("session_number");',
    'CREATE INDEX "FutureTrading_marketsession_captured_at_idx" ON "FutureTrading_marketsession" ("captured_at");',
    'CREATE INDEX "FutureTrading_marketsession_bhs_idx" ON "FutureTrading_marketsession" ("bhs");',
    'CREATE INDEX "FutureTrading_marketsession_wndw_idx" ON "FutureTrading_marketsession" ("wndw");',
]

SETVAL_SQL = """
SELECT setval(
    pg_get_serial_sequence('"FutureTrading_marketsession"', 'id'),
    GREATEST(1, COALESCE((SELECT MAX(id) FROM "FutureTrading_marketsession"), 0)),
    true
);
"""

COLUMN_ORDER_SQL = """
SELECT column_name, ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'FutureTrading_marketsession'
    AND column_name IN ('week_52_low', 'low_pct_52', 'week_52_high', 'high_pct_52')
ORDER BY ordinal_position;
"""


def main() -> None:
    django.setup()
    statements = [CREATE_TABLE_SQL, INSERT_SQL, DROP_TABLE_SQL, RENAME_SQL, *INDEX_SQL, SETVAL_SQL]
    with transaction.atomic():
        with connection.cursor() as cursor:
            for sql in statements:
                cursor.execute(sql)
    with connection.cursor() as cursor:
        cursor.execute(COLUMN_ORDER_SQL)
        rows = cursor.fetchall()
    print("Column order confirmation (position, name):")
    for name_order in rows:
        name = name_order[0]
        position = name_order[1]
        print(f"  {position:03d} -> {name}")


if __name__ == "__main__":
    main()
