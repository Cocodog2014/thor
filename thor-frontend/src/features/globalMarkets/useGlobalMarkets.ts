import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Market } from '../../types';
import marketsService from '../../services/markets';
import { useWsMessage } from '../../realtime';
import type { WsMessage } from '../../realtime/types';
import { qk } from '../../realtime/queryKeys';

export function useGlobalMarkets() {
  const queryClient = useQueryClient();
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isStale, setIsStale] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMarkets = useCallback(async () => {
    const data = await marketsService.getAll();
    return data.results.sort((a, b) => a.sort_order - b.sort_order);
  }, []);

  const marketsQuery = useQuery({
    queryKey: qk.globalMarkets(),
    queryFn: fetchMarkets,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    staleTime: Infinity,
    retry: 1,
  });

  useEffect(() => {
    if (marketsQuery.isError) {
      setError('Lost connection to global markets');
      setIsStale(true);
    } else {
      setError(null);
      setIsStale(false);
    }
  }, [marketsQuery.isError]);

  useWsMessage('global_markets_tick', (msg: WsMessage) => {
    type TickMarket = {
      market_id?: number;
      current_time?: Partial<NonNullable<Market['current_time']>>;
      market_status?: Partial<Market['market_status']>;
      status?: Market['status'];
      market_open_time?: string;
      market_close_time?: string;
    };
    const data = (msg as WsMessage & { data?: { markets?: TickMarket[]; timestamp?: number } }).data;
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

    setLastUpdate(data?.timestamp ? new Date(data.timestamp * 1000) : new Date());
    setIsStale(false);
  });

  return {
    markets: marketsQuery.data ?? [],
    loading: marketsQuery.isLoading || marketsQuery.isFetching,
    error,
    lastUpdate,
    isStale,
  };
}

export type UseGlobalMarketsReturn = ReturnType<typeof useGlobalMarkets>;
