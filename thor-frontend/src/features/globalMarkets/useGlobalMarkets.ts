import { useCallback, useEffect, useRef, useState } from 'react';
import type { Market } from '../../types';
import marketsService from '../../services/markets';
import { useWsMessage } from '../../realtime';

export function useGlobalMarkets() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isStale, setIsStale] = useState(false);

  const bootstrapRef = useRef(false);
  const inFlightRef = useRef(false);

  const fetchMarkets = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    if (!bootstrapRef.current) {
      setLoading(true);
    }

    try {
      const data = await marketsService.getAll();
      const sorted = data.results.sort((a, b) => a.sort_order - b.sort_order);
      setMarkets(sorted);
      setLastUpdate(new Date());
      setError(null);
      setIsStale(false);
    } catch (err) {
      console.error('[GlobalMarkets] fetch failed', err);
      setError('Lost connection to global markets');
      setIsStale(true);
    } finally {
      bootstrapRef.current = true;
      setLoading(false);
      inFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  useWsMessage('market_status', (msg) => {
    const payload = (msg as { data?: Partial<Market> & { market_id?: number; id?: number } }).data;
    if (!payload) return;

    const marketId = payload.market_id ?? payload.id;
    if (!marketId) return;

    setMarkets((prev) => {
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

  useWsMessage('global_markets_tick', (msg) => {
    const data = (msg as { data?: { markets?: Array<{ market_id?: number; current_time?: any }> } }).data;
    const marketsPayload = data?.markets ?? [];
    if (!marketsPayload.length) return;

    setMarkets((prev) => {
      let changed = false;
      const byId = new Map<number, { current_time?: any }>();
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

  return { markets, loading, error, lastUpdate, isStale };
}

export type UseGlobalMarketsReturn = ReturnType<typeof useGlobalMarkets>;
