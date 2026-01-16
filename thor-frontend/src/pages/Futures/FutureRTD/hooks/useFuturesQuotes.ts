import { useCallback, useEffect, useRef, useState } from "react";
import { useWsMessage } from "../../../../realtime";
import { INSTRUMENT_QUOTES_LATEST_ENDPOINT } from "../../../../constants/endpoints";
import type { ApiResponse, MarketData } from "../types";

type QuoteTick = {
  symbol?: string;
  asset_type?: string | null;
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

const FUTURES_ROOTS = new Set([
  'YM',
  'ES',
  'NQ',
  'RTY',
  'CL',
  'SI',
  'HG',
  'GC',
  'VX',
  'DX',
  'ZB',
]);

const _normAssetType = (v: unknown) => String(v ?? "").trim().toUpperCase();

const normalizeFuturesSymbolKey = (symbol: string | undefined | null, assetType?: unknown) => {
  const raw = String(symbol ?? "").trim().toUpperCase();
  if (!raw) return "";

  const at = _normAssetType(assetType);
  const isFut = at.includes("FUTURE") || raw.startsWith("/");
  if (!isFut) return "";

  const base = raw.replace(/^\/+/, "");
  return base ? `/${base}` : "";
};

const canonicalizeFuturesDisplaySymbol = (symbol: string | undefined | null, assetType?: unknown) => {
  const key = normalizeFuturesSymbolKey(symbol, assetType);
  if (!key) return "";
  // If it's a root future we track, keep canonical '/ROOT'. Otherwise keep '/...' as-is.
  const base = key.replace(/^\/+/, "");
  if (FUTURES_ROOTS.has(base)) return `/${base}`;
  return key;
};

const toFloat = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const toPriceString = (value: number | null): string | null => {
  if (value === null) return null;
  return String(value);
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
  const bidNum = toFloat(tick.bid);
  const askNum = toFloat(tick.ask);
  const priceNum =
    toFloat(tick.last) ?? toFloat(tick.price) ?? bidNum ?? askNum ?? null;
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
    price: toPriceString(priceNum),
    bid: toPriceString(bidNum),
    ask: toPriceString(askNum),
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
    spread: computeSpread(bidNum, askNum, null) ?? undefined,
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
        "useFuturesQuotes: fetching",
        INSTRUMENT_QUOTES_LATEST_ENDPOINT,
        new Date().toISOString(),
        `(${reason})`
      );
      const response = await fetch(`${INSTRUMENT_QUOTES_LATEST_ENDPOINT}?consumer=futures_trading`);
      if (!response.ok) {
        throw new Error(`Quote request failed (${response.status})`);
      }

      const data: ApiResponse = await response.json();
      let enrichedRows: MarketData[] = (data.rows || []).map((row) => {
        const displaySymbol = canonicalizeFuturesDisplaySymbol(row?.instrument?.symbol);
        if (!displaySymbol) return row;
        return {
          ...row,
          instrument: {
            ...row.instrument,
            symbol: displaySymbol,
          },
        };
      });

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
          const key = normalizeFuturesSymbolKey(tick.symbol, tick.asset_type);
          if (!key) continue;

          const symbol = canonicalizeFuturesDisplaySymbol(tick.symbol, tick.asset_type);

          const idx = next.findIndex((row) => normalizeFuturesSymbolKey(row.instrument.symbol, "FUTURE") === key);

          const bidNum = toFloat(tick.bid);
          const askNum = toFloat(tick.ask);
          const priceNum =
            toFloat(tick.last) ??
            toFloat(tick.price) ??
            bidNum ??
            askNum ??
            toFloat(next[idx]?.price);
          const volume = toFloat(tick.volume) ?? next[idx]?.volume ?? null;
          const timestamp = toIsoTimestamp(tick.timestamp, next[idx]?.timestamp);
          const spread = computeSpread(bidNum, askNum, next[idx]?.spread);

          if (idx === -1) {
            const row = makeRealtimeRow(
              { ...tick, bid: bidNum, ask: askNum, price: priceNum, volume, timestamp, source: tick.source },
              symbol || key
            );
            next = [...next, row];
            continue;
          }

          const current = next[idx];
          const updated: MarketData = {
            ...current,
            price: toPriceString(priceNum) ?? current.price,
            bid: toPriceString(bidNum) ?? current.bid,
            ask: toPriceString(askNum) ?? current.ask,
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
