// src/pages/Futures/Market/useMarketSessions.ts
import { useEffect, useMemo, useState } from "react";
import {
  type MarketOpenSession,
  type MarketLiveStatus,
  type IntradaySnapshot,
  type IntradayHealth,
  CONTROL_MARKETS,
} from "./marketSessionTypes.ts";
import {
  getApiUrl,
  getLiveStatusApiUrl,
  getSessionApiUrl,
  getIntradayHealthApiUrl,
  normalizeCountry,
  marketKeyToCode,
  buildDateKey,
} from "./marketSessionUtils.ts";

export interface UseMarketSessionsResult {
  sessions: MarketOpenSession[] | null;
  liveStatus: Record<string, MarketLiveStatus>;
  intradayLatest: Record<string, IntradaySnapshot | null>;
  intradayHealth: Record<string, IntradayHealth>;
  selected: Record<string, string>;
  setSelected: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  byCountry: Map<string, MarketOpenSession[]>;
  sessionApiUrl: string;
}

export const useMarketSessions = (apiUrl?: string): UseMarketSessionsResult => {
  const resolvedApiUrl = apiUrl || getApiUrl();
  const resolvedLiveStatusUrl = getLiveStatusApiUrl();
  const resolvedIntradayHealthUrl = useMemo(() => getIntradayHealthApiUrl(), []);
  const sessionApiUrl = useMemo(() => getSessionApiUrl(), []);

  const [sessions, setSessions] = useState<MarketOpenSession[] | null>(null);
  const [liveStatus, setLiveStatus] = useState<Record<string, MarketLiveStatus>>({});
  const [intradayLatest, setIntradayLatest] = useState<Record<string, IntradaySnapshot | null>>({});
  const [intradayHealth, setIntradayHealth] = useState<Record<string, IntradayHealth>>({});

  // Default future per market = TOTAL (per-country composite)
  const [selected, setSelected] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    CONTROL_MARKETS.forEach((m) => {
      init[m.key] = "TOTAL";
    });
    return init;
  });

  // Main sessions + live status fetch (single run)
  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      try {
        const res = await fetch(resolvedApiUrl);
        if (!res.ok) {
          console.error("MarketSessions: API error", res.status, res.statusText);
          if (!cancelled) setSessions([]);
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          const list = Array.isArray(data) ? data : [];
          setSessions(list);
        }
      } catch (e) {
        console.error("MarketSessions: fetch failed", e);
        if (!cancelled) setSessions([]);
      }
    }

    async function loadLiveStatus() {
      try {
        const res = await fetch(resolvedLiveStatusUrl);
        if (!res.ok) {
          console.error("MarketSessions: live status API error", res.status, res.statusText);
          if (!cancelled) setLiveStatus({});
          return;
        }
        const data = await res.json();
        const map: Record<string, MarketLiveStatus> = {};
        if (data && Array.isArray(data.markets)) {
          for (const m of data.markets) {
            if (m && m.country) {
              const ct = m.current_time;
              const localDateKey = ct ? buildDateKey(ct.year, ct.month, ct.date) : undefined;
              map[String(m.country)] = {
                next_event: m.next_event,
                seconds_to_next_event:
                  typeof m.seconds_to_next_event === "number" ? m.seconds_to_next_event : undefined,
                current_state: m.current_state,
                local_date_key: localDateKey,
              };
            }
          }
        }
        if (!cancelled) {
          setLiveStatus(map);
        }
      } catch (e) {
        console.error("MarketSessions: live status fetch failed", e);
        if (!cancelled) setLiveStatus({});
      }
    }

    Promise.all([loadSessions(), loadLiveStatus()]);
    return () => {
      cancelled = true;
    };
  }, [resolvedApiUrl, resolvedLiveStatusUrl]);

  // Intraday health fetch (single run)
  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const res = await fetch(resolvedIntradayHealthUrl);
        if (!res.ok) {
          if (!cancelled) setIntradayHealth({});
          return;
        }
        const data = await res.json();
        const map: Record<string, IntradayHealth> = {};
        if (data && Array.isArray(data.markets)) {
          for (const m of data.markets) {
            const key = m?.market;
            if (!key) continue;
            map[String(key)] = {
              status: m?.status || "unknown",
              last_bar_utc: m?.last_bar_utc ?? null,
              lag_minutes: typeof m?.lag_minutes === "number" ? m.lag_minutes : null,
              threshold_minutes:
                typeof m?.threshold_minutes === "number" ? m.threshold_minutes : data.threshold_minutes || 3,
            };
          }
        }
        if (!cancelled) setIntradayHealth(map);
      } catch (err) {
        console.error("MarketSessions: intraday health fetch failed", err);
        if (!cancelled) setIntradayHealth({});
      }
    }

    loadHealth();
    return () => {
      cancelled = true;
    };
  }, [resolvedIntradayHealthUrl]);

  // Intraday fetch per card / future (excluding TOTAL)
  useEffect(() => {
    let cancelled = false;

    async function loadIntraday() {
      const updates: Record<string, IntradaySnapshot | null> = {};
      await Promise.all(
        CONTROL_MARKETS.map(async (m) => {
          const sel = selected[m.key] || "TOTAL";
          if (sel === "TOTAL") return; // no intraday call for TOTAL composites
          const marketCode = marketKeyToCode(m.key);
          const url = `${sessionApiUrl}?market=${encodeURIComponent(
            marketCode,
          )}&future=${encodeURIComponent(sel)}`;
          try {
            const res = await fetch(url);
            if (!res.ok) {
              updates[m.key] = null;
              return;
            }
            const data = await res.json();
            updates[m.key] = data?.intraday_latest || null;
          } catch (err) {
            console.error("MarketSessions: intraday fetch failed", err);
            updates[m.key] = null;
          }
        }),
      );
      if (!cancelled) setIntradayLatest((prev) => ({ ...prev, ...updates }));
    }

    loadIntraday();
    return () => {
      cancelled = true;
    };
  }, [selected, sessionApiUrl]);

  const byCountry = useMemo(() => {
    const map = new Map<string, MarketOpenSession[]>();
    (sessions || []).forEach((s) => {
      const countryKey = normalizeCountry(s.country);
      if (!map.has(countryKey)) map.set(countryKey, []);
      map.get(countryKey)!.push(s);
    });
    return map;
  }, [sessions]);

  return {
    sessions,
    liveStatus,
    intradayLatest,
    intradayHealth,
    selected,
    setSelected,
    byCountry,
    sessionApiUrl,
  };
};
