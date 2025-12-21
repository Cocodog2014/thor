import { createContext, useContext, useMemo } from 'react';

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
export const GlobalTimerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const value = useMemo<GlobalTimerState>(
    () => ({
      tick: 0,
      now: new Date(),
      marketStatus: null,
      statusError: null,
      refreshMarketStatus: async () => {},
    }),
    [],
  );

  return <GlobalTimerContext.Provider value={value}>{children}</GlobalTimerContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export function useGlobalTimer(): GlobalTimerState {
  const ctx = useContext(GlobalTimerContext);
  if (!ctx) {
    throw new Error('useGlobalTimer must be used within a GlobalTimerProvider');
  }
  return ctx;
}
