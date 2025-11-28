import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, MarketData } from "../types";

type RollingVwapResponse = {
  symbol: string;
  vwap: string | null;
};

export function useFuturesQuotes(pollMs: number) {
  console.log("useFuturesQuotes mounted with poll", pollMs);
  const [rows, setRows] = useState<MarketData[]>([]);
  const [total, setTotal] = useState<ApiResponse["total"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const abortRef = useRef(false);

  useEffect(() => {
    return () => {
      abortRef.current = true;
    };
  }, []);

  const fetchQuotes = useCallback(async () => {
    if (abortRef.current) {
      return;
    }

    if (!hasLoadedOnce) {
      setLoading(true);
    }

    setError(null);

    try {
      const response = await fetch("/api/quotes/latest?consumer=futures_trading");
      if (!response.ok) {
        throw new Error(`Quote request failed (${response.status})`);
      }

      const data: ApiResponse = await response.json();
      let enrichedRows: MarketData[] = data.rows;

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

      if (!abortRef.current) {
        if (!enrichedRows.length) {
          console.warn("useFuturesQuotes: quotes response contained 0 rows");
        }
        setRows(enrichedRows);
        setTotal(data.total ?? null);
      }
    } catch (err) {
      if (!abortRef.current) {
        const message = err instanceof Error ? err.message : "Unknown quotes error";
        console.error("useFuturesQuotes: quotes fetch failed", err);
        setError(message);
      }
    } finally {
      if (!abortRef.current) {
        setHasLoadedOnce(true);
        setLoading(false);
      }
    }
  }, [hasLoadedOnce]);

  useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  useEffect(() => {
    const id = setInterval(() => {
      fetchQuotes();
    }, pollMs);
    return () => clearInterval(id);
  }, [fetchQuotes, pollMs]);

  return { rows, total, loading, error };
}
