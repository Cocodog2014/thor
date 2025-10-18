/**
 * Hook to fetch Schwab account summary data.
 */

import { useState, useEffect } from 'react';

export interface SchwabAccountSummary {
  net_liquidating_value: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  available_funds_for_trading: string;
  long_stock_value: string;
  equity_percentage: string;
  cash_balance: string;
  maintenance_requirement: string;
  margin_balance: string;
  margin_equity?: string;
  money_market_balance?: string;
  settled_funds?: string;
  short_balance?: string;
  short_marginable_value?: string;
  total_commissions_fees_ytd?: string;
}

interface UseSchwabAccountResult {
  summary: SchwabAccountSummary | null;
  loading: boolean;
  error: string | null;
  connected: boolean;
  refresh: () => void;
}

export const useSchwabAccount = (): UseSchwabAccountResult => {
  const [summary, setSummary] = useState<SchwabAccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/schwab/account/summary/', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (response.status === 404) {
        setConnected(false);
        setError('No Schwab account connected. Please complete OAuth setup.');
        setSummary(null);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success && data.summary) {
        setSummary(data.summary);
        setConnected(true);
        setError(null);
      } else {
        throw new Error(data.error || 'Failed to fetch account summary');
      }
    } catch (err) {
      setConnected(false);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  return {
    summary,
    loading,
    error,
    connected,
    refresh: fetchSummary,
  };
};
