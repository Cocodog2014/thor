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

/* 7) Latest session snapshots in custom order (TOTAL, YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB) */
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
  WHEN 'TOTAL' THEN 1
  WHEN 'YM' THEN 2
  WHEN 'ES' THEN 3
  WHEN 'NQ' THEN 4
  WHEN 'RTY' THEN 5
  WHEN 'CL' THEN 6
  WHEN 'SI' THEN 7
  WHEN 'HG' THEN 8
  WHEN 'GC' THEN 9
  WHEN 'VX' THEN 10
  WHEN 'DX' THEN 11
  WHEN 'ZB' THEN 12
  ELSE 999
END;

/* 8) Sessions newest first (explicit ordering: latest on top) */
SELECT id, session_number, year, month, date, day, captured_at
FROM "FutureTrading_marketopensession"
ORDER BY captured_at DESC;