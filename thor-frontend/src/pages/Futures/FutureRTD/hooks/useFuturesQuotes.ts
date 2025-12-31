import { useCallback, useEffect, useRef, useState } from "react";
import { useWsMessage } from "../../../../realtime";
import type { ApiResponse, MarketData } from "../types";

type QuoteTick = {
  symbol?: string;
  bid?: number | string | null;
  ask?: number | string | null;
  last?: number | string | null;
  price?: number | string | null;
  volume?: number | string | null;
  timestamp?: number | string | null;
  source?: string | null;
  exchange?: string | null;
};

type MarketDataSnapshot = {
  timestamp?: number | string | null;
  quotes?: QuoteTick[];
};

const normalizeSymbol = (symbol: string | undefined | null) =>
  (symbol ?? "").replace(/^\//, "").toUpperCase();

const toFloat = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const toIsoTimestamp = (raw: unknown, fallback?: string): string => {
  const num = toFloat(raw);
  if (num === null) return fallback ?? new Date().toISOString();
  const ms = num > 1e12 ? num : num * 1000;
  return new Date(ms).toISOString();
};

const computeSpread = (
  bid: number | null,
  ask: number | null,
  fallback: number | string | null | undefined
): number | null => {
  if (bid === null || ask === null) {
    return toFloat(fallback);
  }
  return ask - bid;
};

const makeRealtimeRow = (tick: QuoteTick, symbol: string): MarketData => {
  const bid = toFloat(tick.bid);
  const ask = toFloat(tick.ask);
  const price =
    toFloat(tick.last) ?? toFloat(tick.price) ?? bid ?? ask ?? null;
  return {
    instrument: {
      id: Date.now(),
      symbol,
      name: symbol,
      exchange: tick.exchange ?? "—",
      currency: "USD",
      display_precision: 2,
      tick_value: null,
      margin_requirement: null,
      is_active: true,
      sort_order: 0,
    },
    price,
    bid,
    ask,
    last_size: null,
    bid_size: null,
    ask_size: null,
    open_price: null,
    high_price: null,
    low_price: null,
    close_price: null,
    previous_close: null,
    change: null,
    change_percent: null,
    vwap: null,
    volume: toFloat(tick.volume),
    market_status: "OPEN",
    data_source: tick.source ?? "realtime",
    is_real_time: true,
    delay_minutes: 0,
    extended_data: {},
    timestamp: toIsoTimestamp(tick.timestamp),
    spread: computeSpread(bid, ask, null) ?? undefined,
  } as MarketData;
};

type RollingVwapResponse = {
  symbol: string;
  vwap: string | null;
};

type UseFuturesQuotesResult = {
  rows: MarketData[];
  total: ApiResponse["total"] | null;
  loading: boolean;
  error: string | null;
  hasLoadedOnce: boolean;
};

export function useFuturesQuotes(): UseFuturesQuotesResult {

  const [rows, setRows] = useState<MarketData[]>([]);
  const [total, setTotal] = useState<ApiResponse["total"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  // Prevent state updates after unmount (handles React StrictMode double-mount in dev)
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchQuotes = useCallback(async (reason: "initial" | "manual" = "initial") => {

    if (!hasLoadedOnce) {
      setLoading(true);
    }

    setError(null);

    try {
      console.log(
        "useFuturesQuotes: fetching /api/quotes/latest",
        new Date().toISOString(),
        `(${reason})`
      );
      const response = await fetch("/api/quotes/latest?consumer=futures_trading");
      if (!response.ok) {
        throw new Error(`Quote request failed (${response.status})`);
      }

      const data: ApiResponse = await response.json();
      let enrichedRows: MarketData[] = data.rows;

      console.log("useFuturesQuotes: quotes response", {
        rowCount: enrichedRows.length,
        totalKeys: Object.keys(data.total ?? {}).length,
      });

      const symbols = data.rows.map((row) => row.instrument.symbol).filter(Boolean);
      if (symbols.length > 0) {
        try {
          const vwapResponse = await fetch(
            `/api/vwap/rolling?symbols=${symbols.join(",")}&minutes=30`
          );
          if (vwapResponse.ok) {
            const vwapData: RollingVwapResponse[] = await vwapResponse.json();
            enrichedRows = data.rows.map((row) => {
              const found = vwapData.find((vw) => vw.symbol === row.instrument.symbol);
              return found ? { ...row, vwap: found.vwap } : row;
            });
          }
        } catch (vwErr) {
          console.warn("VWAP fetch failed", vwErr);
        }
      }

      if (mountedRef.current) {
        if (!enrichedRows.length) {
          console.warn("useFuturesQuotes: quotes response contained 0 rows");
        }
        setRows(enrichedRows);
        setTotal(data.total ?? null);
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : "Unknown quotes error";
        console.error("useFuturesQuotes: quotes fetch failed", err);
        setError(message);
      }
    } finally {
      if (mountedRef.current) {
        setHasLoadedOnce(true);
        setLoading(false);
      }
    }
  }, [hasLoadedOnce]);

  useEffect(() => {
    fetchQuotes("initial");
  }, [fetchQuotes]);

  useWsMessage<MarketDataSnapshot>(
    "market_data",
    (msg) => {
      const data = msg.data;
      const quotes = data?.quotes;
      if (!quotes || !Array.isArray(quotes) || !quotes.length) return;

      // Apply the whole snapshot in one state update.
      setRows((prev) => {
        let next = prev;

        for (const tick of quotes) {
          if (!tick) continue;
          const symbol = normalizeSymbol(tick.symbol);
          if (!symbol) continue;

          const idx = next.findIndex((row) => normalizeSymbol(row.instrument.symbol) === symbol);

          const bid = toFloat(tick.bid);
          const ask = toFloat(tick.ask);
          const price =
            toFloat(tick.last) ??
            toFloat(tick.price) ??
            bid ??
            ask ??
            toFloat(next[idx]?.price);
          const volume = toFloat(tick.volume) ?? next[idx]?.volume ?? null;
          const timestamp = toIsoTimestamp(tick.timestamp, next[idx]?.timestamp);
          const spread = computeSpread(bid, ask, next[idx]?.spread);

          if (idx === -1) {
            const row = makeRealtimeRow(
              { ...tick, bid, ask, price, volume, timestamp, source: tick.source },
              symbol
            );
            next = [...next, row];
            continue;
          }

          const current = next[idx];
          const updated: MarketData = {
            ...current,
            price,
            bid: bid ?? current.bid,
            ask: ask ?? current.ask,
            volume,
            data_source: tick.source ?? current.data_source,
            is_real_time: true,
            timestamp,
            spread,
          };

          const copy = [...next];
          copy[idx] = updated;
          next = copy;
        }

        return next;
      });
    },
    true
  );

  return { rows, total, loading, error, hasLoadedOnce };
}
