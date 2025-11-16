-- Thor DB quick inspection queries
-- Attach this editor to the connection: Thor PostgreSQL (Docker)
-- Run each block with the Run button (Ctrl+Enter)

/* 1) List all public tables */
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

/* 2) Count rows in MarketOpenSession */
SELECT COUNT(*) AS session_rows
FROM "FutureTrading_marketopensession";

/* 3) Latest 20 MarketOpen sessions */
SELECT id, market_key, captured_at
FROM "FutureTrading_marketopensession"
ORDER BY captured_at DESC
LIMIT 20;

/* 4) Latest session id */
SELECT id AS latest_session_id
FROM "FutureTrading_marketopensession"
ORDER BY captured_at DESC
LIMIT 1;

/* 5) Snapshots for the latest session */
SELECT s.symbol,
       s.last_price,
       s.signal,
       s.weight
FROM "FutureTrading_futuresnapshot" s
JOIN (
  SELECT id
  FROM "FutureTrading_marketopensession"
  ORDER BY captured_at DESC
  LIMIT 1
) latest ON s.session_id = latest.id
ORDER BY s.symbol;

/* 6) Recent Global Market Index rows */
SELECT id, timestamp, global_composite_score, active_markets_count, session_phase
FROM "GlobalMarkets_globalmarketindex"
ORDER BY timestamp DESC
LIMIT 50;

/* 7) Latest session snapshots in custom order (ZB, DX, VX, GC, HG, SI, CL, RTY, NQ, ES, YM, TOTAL) */
WITH latest AS (
  SELECT id FROM "FutureTrading_marketopensession" ORDER BY captured_at DESC LIMIT 1
)
SELECT s.symbol,
       s.last_price,
       s.signal,
       s.weight
FROM "FutureTrading_futuresnapshot" s
JOIN latest l ON s.session_id = l.id
ORDER BY CASE UPPER(s.symbol)
  WHEN 'ZB' THEN 1
  WHEN 'DX' THEN 2
  WHEN 'VX' THEN 3
  WHEN 'GC' THEN 4
  WHEN 'HG' THEN 5
  WHEN 'SI' THEN 6
  WHEN 'CL' THEN 7
  WHEN 'RTY' THEN 8
  WHEN 'NQ' THEN 9
  WHEN 'ES' THEN 10
  WHEN 'YM' THEN 11
  WHEN 'TOTAL' THEN 12
  ELSE 999
END, UPPER(s.symbol);

/* 8) Sessions newest first (explicit ordering: latest on top) */
SELECT id, session_number, year, month, date, day, captured_at
FROM "FutureTrading_marketopensession"
ORDER BY captured_at DESC;