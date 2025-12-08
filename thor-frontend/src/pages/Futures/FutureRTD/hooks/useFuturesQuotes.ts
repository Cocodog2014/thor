import { useCallback, useEffect, useRef, useState } from "react";
import { useGlobalTimer } from "../../../../context/GlobalTimerContext";
import type { ApiResponse, MarketData } from "../types";

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

export function useFuturesQuotes(pollMs: number): UseFuturesQuotesResult {
  console.log("useFuturesQuotes mounted with poll", pollMs);

  const { tick } = useGlobalTimer();
  const pollEveryTicks = Math.max(1, Math.round(pollMs / 1000));

  const [rows, setRows] = useState<MarketData[]>([]);
  const [total, setTotal] = useState<ApiResponse["total"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [nextFetchTick, setNextFetchTick] = useState(0);
  // Prevent state updates after unmount (handles React StrictMode double-mount in dev)
  const mountedRef = useRef(true);
  const bootstrapRef = useRef(false);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchQuotes = useCallback(async (reason: "initial" | "timer", currentTick: number) => {

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
        bootstrapRef.current = true;
        setNextFetchTick(currentTick + pollEveryTicks);
      }
    }
  }, [hasLoadedOnce, pollEveryTicks]);

  useEffect(() => {
    fetchQuotes("initial", 0);
  }, [fetchQuotes]);

  useEffect(() => {
    if (!bootstrapRef.current) return;
    if (tick === 0) return;
    if (tick < nextFetchTick) return;
    fetchQuotes("timer", tick);
  }, [fetchQuotes, nextFetchTick, tick]);

  return { rows, total, loading, error, hasLoadedOnce };
}
