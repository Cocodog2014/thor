import { useCallback, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import marketsService from '../../services/markets';
import { useWsConnection, useWsMessage } from '../../realtime';
import type { WsEnvelope } from '../../realtime/types';
import { qk } from '../../realtime/queryKeys';

import type { Market } from '../../types';

type GlobalMarketsTickPayload = {
  server_time_utc?: string;
  markets?: Array<{
    key: string;
    name?: string;
    status?: string;
    next_transition_utc?: string | null;
  }>;
};

export function useGlobalMarkets() {
  const queryClient = useQueryClient();
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsConnected = useWsConnection();

  const fetchMarkets = useCallback(async () => {
    return await marketsService.getAll();
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

  useWsMessage<GlobalMarketsTickPayload>('global_markets_tick', (msg: WsEnvelope<GlobalMarketsTickPayload>) => {
    const data = msg.data;
    const marketsPayload = data?.markets ?? [];
    if (!marketsPayload.length) return;

    queryClient.setQueryData<Market[] | undefined>(qk.globalMarkets(), (prev) => {
      if (!prev) return prev;
      const byKey = new Map<string, (typeof marketsPayload)[number]>();
      for (const m of marketsPayload) {
        if (m?.key) byKey.set(m.key, m);
      }
      if (!byKey.size) return prev;

      let changed = false;
      const next = prev.map((m) => {
        const incoming = m?.key ? byKey.get(m.key) : undefined;
        if (!incoming) return m;

        const updated: Market = { ...m };
        if (incoming.name && incoming.name !== m.name) updated.name = incoming.name;
        if (incoming.name && incoming.name !== m.display_name) updated.display_name = incoming.name;

        if (incoming.status && incoming.status !== m.status) {
          updated.status = incoming.status;
          changed = true;
        }

        if (incoming.next_transition_utc !== undefined && incoming.next_transition_utc !== m.next_transition_utc) {
          updated.next_transition_utc = incoming.next_transition_utc ?? null;
          changed = true;
        }

        return updated;
      });

      return changed ? next : prev;
    });

    setLastUpdate(data?.server_time_utc ? new Date(data.server_time_utc) : new Date());
    setError(null);
  });

  return {
    markets: marketsQuery.data ?? [],
    // Avoid flashing the whole table during background refetches.
    loading: marketsQuery.isLoading,
    error: marketsQuery.isError ? 'Lost connection to global markets' : error,
    lastUpdate,
    isStale: !wsConnected,
  };
}

export type UseGlobalMarketsReturn = ReturnType<typeof useGlobalMarkets>;
