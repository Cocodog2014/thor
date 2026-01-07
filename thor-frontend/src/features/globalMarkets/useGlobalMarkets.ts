import { useCallback, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Market } from '../../types';
import marketsService from '../../services/markets';
import { useWsConnection, useWsMessage } from '../../realtime';
import type { WsEnvelope } from '../../realtime/types';
import { qk } from '../../realtime/queryKeys';

type TickMarket = {
  market_id?: number;
  current_time?: Partial<NonNullable<Market['current_time']>>;
  market_status?: Partial<Market['market_status']>;
  status?: Market['status'];
  market_open_time?: string;
  market_close_time?: string;
};

export function useGlobalMarkets() {
  const queryClient = useQueryClient();
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsConnected = useWsConnection();

  const fetchMarkets = useCallback(async () => {
    const data = await marketsService.getAll();
    return data.results;
  }, []);

  const marketsQuery = useQuery({
    queryKey: qk.globalMarkets(),
    queryFn: fetchMarkets,
    // If the WebSocket drops, keep the UI moving via REST until it reconnects.
    // This prevents the "works for a few seconds then freezes" symptom.
    refetchInterval: wsConnected ? false : 5000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    staleTime: Infinity,
    retry: 1,
  });

  useWsMessage<{ markets?: TickMarket[]; timestamp?: number }>('global_markets_tick', (msg: WsEnvelope<{ markets?: TickMarket[]; timestamp?: number }>) => {
    const { data, ts } = msg;
    const marketsPayload = data?.markets ?? [];
    if (!marketsPayload.length) return;

    queryClient.setQueryData<Market[] | undefined>(qk.globalMarkets(), (prev) => {
      if (!prev) return prev;
      let changed = false;
      const byId = new Map<number, TickMarket>();
      for (const m of marketsPayload) {
        if (m.market_id != null) byId.set(m.market_id, m);
      }
      if (!byId.size) return prev;

      const next = prev.map((m) => {
        const incoming = byId.get(m.id);
        if (!incoming) return m;

        const updated: Market = { ...m } as Market;

        if (incoming.market_open_time) {
          updated.market_open_time = incoming.market_open_time;
        }
        if (incoming.market_close_time) {
          updated.market_close_time = incoming.market_close_time;
        }

        if (incoming.current_time) {
          changed = true;
          updated.current_time = { ...m.current_time, ...incoming.current_time };
        }

        if (incoming.market_status) {
          changed = true;
          updated.market_status = {
            ...m.market_status,
            ...incoming.market_status,
            current_time:
              (incoming.market_status.current_time as Market['market_status']['current_time']) ?? m.market_status.current_time,
          } as Market['market_status'];
        }

        if (incoming.status) {
          changed = true;
          updated.status = incoming.status;
        }

        return updated;
      });

      return changed ? next : prev;
    });

    const stamp = ts ?? (data?.timestamp as number | undefined);
    setLastUpdate(stamp ? new Date(stamp * 1000) : new Date());
    setError(null);
  });

  return {
    markets: marketsQuery.data ?? [],
    loading: marketsQuery.isLoading || marketsQuery.isFetching,
    error: marketsQuery.isError ? 'Lost connection to global markets' : error,
    lastUpdate,
    isStale: !wsConnected,
  };
}

export type UseGlobalMarketsReturn = ReturnType<typeof useGlobalMarkets>;
