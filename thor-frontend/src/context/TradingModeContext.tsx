import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export type TradingMode = 'live' | 'paper';

type TradingModeContextValue = {
  mode: TradingMode;
  setMode: (m: TradingMode) => void;
};

const TradingModeContext = createContext<TradingModeContextValue | undefined>(undefined);

const LOCAL_STORAGE_KEY = 'thor_trading_mode';

export const TradingModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<TradingMode>(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY) as TradingMode | null;
      return saved === 'paper' || saved === 'live' ? saved : 'live';
    } catch {
      return 'live';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, mode);
    } catch {
      // ignore persistence errors
    }
  }, [mode]);

  const value = useMemo(() => ({ mode, setMode }), [mode]);

  return <TradingModeContext.Provider value={value}>{children}</TradingModeContext.Provider>;
};

export function useTradingMode(): TradingModeContextValue {
  const ctx = useContext(TradingModeContext);
  if (!ctx) throw new Error('useTradingMode must be used within a TradingModeProvider');
  return ctx;
}
