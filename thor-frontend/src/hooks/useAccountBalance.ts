import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import api from "../services/api";
import { qk } from "../realtime/queryKeys";
import { getWebSocketManager } from "../services/websocket";
import { wssCutover } from "../services/websocket-cutover";
import type { BackendMessage } from "../services/websocket";

export type AccountBalance = {
  account_id: string;
  net_liquidation: number;
  equity: number;
  cash: number;
  buying_power: number;
  day_trade_bp: number;
  updated_at: string;
  source?: string;
};

async function fetchAccountBalance(accountId?: string | null) {
  const res = await api.get<AccountBalance>("/accounts/balance/", {
    params: accountId ? { account_id: accountId } : undefined,
  });
  return res.data;
}

export function useAccountBalance(accountId?: string | null) {
  const accountKey = accountId ? `acct:${accountId}` : "acct:none";
  const [wsBalance, setWsBalance] = useState<AccountBalance | null>(null);
  const useWebSocket = wssCutover.isWebSocketEnabled('account_balance');

  // Subscribe to WebSocket updates if enabled
  useEffect(() => {
    if (!useWebSocket) return;

    const ws = getWebSocketManager();
    
    const handleMessage = (msg: BackendMessage) => {
      if (msg.type === 'account_balance' && 'data' in msg) {
        const data = msg.data as any;
        // Map backend format to frontend format
        setWsBalance({
          account_id: data.account_id || accountId || '',
          net_liquidation: data.portfolio_value || 0,
          equity: data.equity || 0,
          cash: data.cash || 0,
          buying_power: data.buying_power || 0,
          day_trade_bp: 0,
          updated_at: new Date(data.timestamp * 1000).toISOString(),
          source: 'websocket',
        });
      }
    };

    ws.on('account_balance', handleMessage);
    return () => ws.off('account_balance', handleMessage);
  }, [useWebSocket, accountId]);

  const query = useQuery({
    queryKey: qk.balances(accountKey),
    queryFn: () => fetchAccountBalance(accountId),
    refetchInterval: false,
    refetchOnWindowFocus: false,
    retry: 1,
    initialData: wsBalance || undefined,
  });

  // If WebSocket is enabled and we have fresh data, use it
  if (useWebSocket && wsBalance) {
    return {
      ...query,
      data: wsBalance,
    };
  }

  return query;
}
