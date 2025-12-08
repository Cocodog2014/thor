import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import api from '../services/api';

export type MarketStatusSummary = {
  usMarketOpen: boolean;
  activeMarkets: number;
  totalMarkets: number;
  currentlyTrading: string[];
  lastUpdated: string;
};

export type GlobalTimerState = {
  tick: number;
  now: Date;
  marketStatus: MarketStatusSummary | null;
  statusError: string | null;
  refreshMarketStatus: () => Promise<void>;
};

const GlobalTimerContext = createContext<GlobalTimerState | undefined>(undefined);

const STATUS_REFRESH_INTERVAL_TICKS = 10; // every 10 seconds

export const GlobalTimerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tick, setTick] = useState(0);
  const [now, setNow] = useState(() => new Date());
  const [marketStatus, setMarketStatus] = useState<MarketStatusSummary | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const fetchingStatus = useRef(false);

  useEffect(() => {
    const id = window.setInterval(() => {
      setTick((prev) => (prev === Number.MAX_SAFE_INTEGER ? 0 : prev + 1));
      setNow(new Date());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const refreshMarketStatus = useCallback(async () => {
    if (fetchingStatus.current) return;
    fetchingStatus.current = true;
    try {
      const { data } = await api.get('/global-markets/stats/');
      setMarketStatus({
        usMarketOpen: Boolean(data?.us_market_open),
        activeMarkets: Number(data?.active_markets ?? 0),
        totalMarkets: Number(data?.total_markets ?? 0),
        currentlyTrading: Array.isArray(data?.currently_trading) ? data.currently_trading : [],
        lastUpdated: new Date().toISOString(),
      });
      setStatusError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to refresh market status';
      setStatusError(message);
    } finally {
      fetchingStatus.current = false;
    }
  }, []);

  useEffect(() => {
    // initial fetch
    refreshMarketStatus();
  }, [refreshMarketStatus]);

  useEffect(() => {
    if (tick === 0) return;
    if (tick % STATUS_REFRESH_INTERVAL_TICKS === 0) {
      refreshMarketStatus();
    }
  }, [tick, refreshMarketStatus]);

  const value = useMemo<GlobalTimerState>(
    () => ({ tick, now, marketStatus, statusError, refreshMarketStatus }),
    [tick, now, marketStatus, statusError, refreshMarketStatus],
  );

  return <GlobalTimerContext.Provider value={value}>{children}</GlobalTimerContext.Provider>;
};

export function useGlobalTimer(): GlobalTimerState {
  const ctx = useContext(GlobalTimerContext);
  if (!ctx) {
    throw new Error('useGlobalTimer must be used within a GlobalTimerProvider');
  }
  return ctx;
}
