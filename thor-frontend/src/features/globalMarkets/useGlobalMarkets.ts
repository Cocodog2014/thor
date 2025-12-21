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

  useWsMessage('market_status', (msg: WsMessage) => {
    const payload = (msg as WsMessage & { data?: Partial<Market> & { market_id?: number; id?: number; current_time?: Market['current_time'] } }).data;
    if (!payload) return;

    const marketId = payload.market_id ?? payload.id;
    if (!marketId) return;

    queryClient.setQueryData<Market[] | undefined>(qk.globalMarkets(), (prev) => {
      if (!prev) return prev;
      const idx = prev.findIndex((m) => m.id === marketId);
      if (idx === -1) return prev;

      const next = [...prev];
      const current = next[idx];

      next[idx] = {
        ...current,
        status: payload.status ?? current.status,
        market_status: {
          ...current.market_status,
          ...(payload.market_status ?? {}),
        },
        current_time: payload.current_time
          ? { ...current.current_time, ...payload.current_time }
          : current.current_time,
      } as Market;

      return next;
    });

    setLastUpdate(new Date());
    setIsStale(false);
  });

  useWsMessage('global_markets_tick', (msg: WsMessage) => {
    type TickMarket = { market_id?: number; current_time?: Partial<NonNullable<Market['current_time']>> };
    const data = (msg as WsMessage & { data?: { markets?: TickMarket[] } }).data;
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
        if (!incoming || !incoming.current_time) return m;
        changed = true;
        return {
          ...m,
          current_time: { ...m.current_time, ...incoming.current_time },
          market_status: {
            ...m.market_status,
            current_time: incoming.current_time.timestamp ?? m.market_status.current_time,
          },
        } as Market;
      });

      return changed ? next : prev;
    });

    setLastUpdate(new Date());
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
