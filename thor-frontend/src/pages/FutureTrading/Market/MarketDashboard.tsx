import React, { useEffect, useMemo, useState } from "react";
// Styles are imported globally via src/styles/global.css

// ---- Types ----
interface FutureSnapshot {
  symbol?: string | null;
  bid?: string | null;
  bid_size?: number | null;
  ask?: string | null;
  ask_size?: number | null;
  volume?: number | null;
  vwap?: string | null;
  open?: string | null;
  close?: string | null;
  day_24h_low?: string | null;
  day_24h_high?: string | null;
  range_high_low?: string | null;
  range_percent?: string | null;
  week_52_low?: string | null;
  week_52_high?: string | null;
  // TOTAL-specific fields
  weighted_average?: string | null;
  signal?: string | null;
  sum_weighted?: string | null;
  instrument_count?: number | null;
  status?: string | null;
}

interface MarketOpenSession {
  id: number;
  captured_at: string; // ISO time
  country: string;     // backend uses canonical market country (e.g., "Japan")
  total_signal: string; // BUY / SELL / STRONG_BUY / STRONG_SELL / HOLD
  fw_nwdw: string;      // WORKED / DIDNT_WORK / PENDING
  ym_entry_price?: string | null;
  fw_exit_value?: string | null;
  fw_exit_percent?: string | null;
  futures?: FutureSnapshot[];
}

// ---- Fixed control markets in display order (UI labels) ----
const CONTROL_MARKETS = [
  { key: "Tokyo", label: "Tokyo", country: "Japan" },
  { key: "Shanghai", label: "Shanghai", country: "China" },
  { key: "Bombay", label: "Bombay", country: "India" },
  { key: "Frankfurt", label: "Frankfurt", country: "Germany" },
  { key: "London", label: "London", country: "United Kingdom" },
  { key: "Pre_USA", label: "Pre_USA", country: "Pre_USA" },
  { key: "USA", label: "USA", country: "USA" },
  { key: "Toronto", label: "Toronto", country: "Canada" },
  { key: "Mexican", label: "Mexican", country: "Mexico" },
] as const;

// Futures universe: 10 futures + Dollar Index + TOTAL (composite)
const FUTURE_OPTIONS = [
  { key: "YM",   label: "YM (Dow)" },
  { key: "ES",   label: "ES (S&P)" },
  { key: "NQ",   label: "NQ (Nasdaq)" },
  { key: "RTY",  label: "RTY (Russell)" },
  { key: "CL",   label: "CL (Crude)" },
  { key: "GC",   label: "GC (Gold)" },
  { key: "SI",   label: "SI (Silver)" },
  { key: "HG",   label: "HG (Copper)" },
  { key: "VX",   label: "VX (VIX)" },
  { key: "ZB",   label: "ZB (30Y)" },
  { key: "DX",   label: "DX (Dollar)" },
  { key: "TOTAL",label: "TOTAL (Composite)" },
] as const;

const chipClass = (kind: "signal" | "status", value?: string) => {
  const base = "mo-rt-chip";
  if (!value) return `${base} default`;
  const v = (value || "").toUpperCase();
  if (kind === "signal") {
    if (v === "BUY" || v === "STRONG_BUY") return `${base} success`;
    if (v === "SELL" || v === "STRONG_SELL") return `${base} error`;
    if (v === "HOLD") return `${base} warning`;
    return `${base} default`;
  }
  if (v === "WORKED") return `${base} success`;
  if (v === "DIDNT_WORK") return `${base} error`;
  if (v === "PENDING") return `${base} warning`;
  return `${base} default`;
};

const formatNum = (n?: string | null, maxFrac = 2) => {
  if (!n) return undefined;
  const s = String(n);
  const p = Number(s.replace(/,/g, ""));
  if (Number.isNaN(p)) return s;
  return p.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
};

const MarketDashboard: React.FC<{ apiUrl?: string }> = ({ apiUrl = "http://127.0.0.1:8000/api/market-opens/latest/" }) => {
  const [sessions, setSessions] = useState<MarketOpenSession[] | null>(null);
  const [liveStatus, setLiveStatus] = useState<Record<string, { next_event?: string; seconds_to_next_event?: number }>>({});
  const [selected, setSelected] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    CONTROL_MARKETS.forEach(m => { init[m.key] = FUTURE_OPTIONS[0].key; }); // default YM
    return init;
  });

  useEffect(() => {
    let cancelled = false;
    let running = false; // prevent overlapping fetches when interval is < network latency
    async function loadSessions() {
      try {
        const res = await fetch(apiUrl);
        const data = await res.json();
        if (!cancelled) setSessions(Array.isArray(data) ? data : []);
      } catch (e) {
        if (!cancelled) setSessions([]);
      }
    }
    async function loadLiveStatus() {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/global-markets/markets/live_status/");
        const data = await res.json();
        const map: Record<string, { next_event?: string; seconds_to_next_event?: number }> = {};
        if (data && Array.isArray(data.markets)) {
          for (const m of data.markets) {
            if (m && m.country) {
              map[String(m.country)] = {
                next_event: m.next_event,
                seconds_to_next_event: typeof m.seconds_to_next_event === 'number' ? m.seconds_to_next_event : undefined,
              };
            }
          }
        }
        if (!cancelled) setLiveStatus(map);
      } catch (e) {
        if (!cancelled) setLiveStatus({});
      }
    }
    async function tick() {
      if (running) return;
      running = true;
      try {
        await Promise.all([loadSessions(), loadLiveStatus()]);
      } finally {
        running = false;
      }
    }
    tick();
    const id = setInterval(tick, 1000); // update every second
    return () => { cancelled = true; clearInterval(id); };
  }, [apiUrl]);

  // Map backend sessions by canonical country (Japan, Germany, etc.)
  const byCountry = useMemo(() => {
    const map = new Map<string, MarketOpenSession>();
    (sessions || []).forEach(s => map.set((s.country || "").trim(), s));
    return map;
  }, [sessions]);

  const isToday = (iso?: string) => {
    if (!iso) return false;
    const d = new Date(iso);
    const now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  };

  // Find the most recent session with a TOTAL snapshot
  const totalSession = useMemo(() => {
    const allSessions = Array.from(byCountry.values()).sort((a, b) => 
      new Date(b.captured_at).getTime() - new Date(a.captured_at).getTime()
    );
    
    // Debug: log what we have
    console.log('🔍 Total sessions found:', allSessions.length);
    if (allSessions.length > 0) {
      console.log('🔍 First session futures:', allSessions[0].futures?.length || 0);
      if (allSessions[0].futures) {
        console.log('🔍 Symbols:', allSessions[0].futures.map(f => f.symbol));
      }
    }
    
    for (const s of allSessions) {
      const totalSnap = (s.futures || []).find(f => (f.symbol || "").toUpperCase() === "TOTAL");
      if (totalSnap) {
        console.log('✅ Found TOTAL snapshot in session:', s.country);
        return { session: s, snap: totalSnap };
      }
    }
    console.log('❌ No TOTAL snapshot found');
    
    // Fallback: use any session and show placeholder
    if (allSessions.length > 0) {
      return { 
        session: allSessions[0], 
        snap: { 
          symbol: 'TOTAL',
          weighted_average: null, 
          signal: null, 
          sum_weighted: null, 
          instrument_count: null, 
          status: 'No data yet' 
        } 
      };
    }
    return null;
  }, [byCountry]);

  return (
    <div className="market-dashboard">
      <div className="market-dashboard-header">
        <h3 className="market-open-header-title">📊 Market Open Sessions</h3>
        <div className="text-xs" style={{ opacity: 0.9 }}>Always shows all 9 control markets</div>
      </div>

      {/* TOTAL Composite Card - always show, spans 3 columns */}
      <div className="total-composite-card">
        <div className="total-header">
          <span className="total-title">TOTAL</span>
          <span className="total-badge composite">Composite</span>
          <span className="total-badge futures">11 Futures</span>
          {totalSession && (
            <span
              className={`total-pill ${String(totalSession.session.total_signal || '').toLowerCase().replace('_','-')}`}
            >
              {(totalSession.session.total_signal || '—').replace('_',' ')}
            </span>
          )}
          <span className="total-time">
            {totalSession?.session.captured_at ? new Date(totalSession.session.captured_at).toLocaleTimeString() : "—"}
          </span>
        </div>
        {totalSession ? (
          <div className="total-body">
            <div className="total-left">
              <div className="total-val">{formatNum(String(totalSession.snap.weighted_average), 3) || '—'}</div>
              <div className="total-label">Weighted Average</div>
              <div className="total-left-metrics">
                <div className="total-mini-card">
                  <div className="mini-title">Sum</div>
                  <div className="mini-value">{formatNum(totalSession.snap.sum_weighted) || '—'}</div>
                  <div className="mini-sub">Weighted</div>
                </div>
                <div className="total-mini-card">
                  <div className="mini-title">Count</div>
                  <div className="mini-value">{totalSession.snap.instrument_count ?? '—'}</div>
                  <div className="mini-sub">Instruments</div>
                </div>
              </div>
            </div>
            <div className="total-right">
              <div className="wgt">Wgt: {String((totalSession.snap as any).weight ?? '—')}</div>
              <div className="live-label">LIVE TOTAL</div>
            </div>
          </div>
        ) : (
          <div className="total-empty">🪫 No TOTAL data captured yet — waiting for market open…</div>
        )}
      </div>

      <div className="market-grid">
        {CONTROL_MARKETS.map(m => {
          const s = byCountry.get(m.country);
          const status = liveStatus[m.country];
          const seconds = status?.seconds_to_next_event ?? undefined;
          const nextEvent = status?.next_event;

          // Keep prior day's card visible until 5 minutes (300s) before today's open
          const isPriorDay = s?.captured_at ? !isToday(s.captured_at) : false;
          const hidePriorNow = isPriorDay && nextEvent === 'open' && typeof seconds === 'number' && seconds <= 300;
          if (hidePriorNow) {
            return (
              <div key={m.key} className="mo-rt-card">
                <div className="mo-rt-header">
                  <span className="mo-rt-chip sym">{m.label}</span>
                  <span className="mo-rt-chip default">—</span>
                  <span className="mo-rt-time">Starting soon…</span>
                </div>
                <div className="mo-rt-body">
                  <div className="mo-rt-top">
                    <div className="mo-rt-last"><div className="val">—</div><div className="label">Last</div></div>
                    <div className="mo-rt-change"><div className="val">—</div><div className="pct">—%</div><div className="label">Change</div></div>
                  </div>
                </div>
              </div>
            );
          }
          const time = s?.captured_at ? new Date(s.captured_at).toLocaleTimeString() : "—";
          const signal = s?.total_signal;
          const outcomeStatus = s?.fw_nwdw;

          const selectedSymbol = selected[m.key];
          const snap: FutureSnapshot | undefined = (s?.futures || []).find(f =>
            (f.symbol || "").toUpperCase() === (selectedSymbol || "").toUpperCase()
          ) || (s?.futures || [])[0];

          return (
            <div key={m.key} className="mo-rt-card">
              <div className="mo-rt-header">
                <span className="mo-rt-chip sym">{m.label}</span>
                <span className={chipClass("signal", signal)}>{signal || "—"}</span>
                <span className={chipClass("status", outcomeStatus)}>{outcomeStatus || "—"}</span>
                <span className="mo-rt-chip">Wgt: —</span>
                <span className="mo-rt-time">{time}</span>
              </div>

              <div className="mo-rt-body">
                {/* Chips + Future Dropdown */}
                <div className="flex" style={{ display:'flex', alignItems:'center', gap:8, marginBottom:12 }}>
                  <div style={{ marginLeft: 'auto' }}>
                    <label className="future-select-label">Future</label>
                    <select
                      className="future-select"
                      value={selected[m.key]}
                      onChange={(e) => setSelected(prev => ({ ...prev, [m.key]: e.target.value }))}
                    >
                      {FUTURE_OPTIONS.map(o => (
                        <option key={o.key} value={o.key}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Top: Last & Change */}
                <div className="mo-rt-top">
                  <div className="mo-rt-last">
                    <div className="val">{formatNum(s?.ym_entry_price) ?? '—'}</div>
                    <div className="label">Last</div>
                  </div>
                  <div className="mo-rt-change">
                    <div className="val">—</div>
                    <div className="pct">—%</div>
                    <div className="label">Change</div>
                  </div>
                </div>

                {/* BBO tiles */}
                <div className="mo-rt-bbo">
                  <div className="tile bid">
                    <div className="t-head">BID</div>
                    <div className="t-main">{snap?.bid ?? '—'}</div>
                    <div className="t-sub">Size {snap?.bid_size ?? '—'}</div>
                  </div>
                  <div className="tile ask">
                    <div className="t-head">ASK</div>
                    <div className="t-main">{snap?.ask ?? '—'}</div>
                    <div className="t-sub">Size {snap?.ask_size ?? '—'}</div>
                  </div>
                </div>

                {/* Stats grid */}
                <div className="mo-rt-stats">
                  <div className="stat"><div className="label">Volume</div><div className="value">{snap?.volume?.toLocaleString() ?? '—'}</div></div>
                  <div className="stat"><div className="label">VWAP</div><div className="value">{snap?.vwap ?? '—'}</div></div>
                  <div className="stat"><div className="label">Close</div><div className="value">{snap?.close ?? '—'}</div></div>
                  <div className="stat"><div className="label">Open</div><div className="value">{snap?.open ?? '—'}</div></div>
                  <div className="stat"><div className="label">24h Low</div><div className="value">{snap?.day_24h_low ?? '—'}</div></div>
                  <div className="stat"><div className="label">24h High</div><div className="value">{snap?.day_24h_high ?? '—'}</div></div>
                  <div className="stat"><div className="label">24h Range</div><div className="value">{snap?.range_high_low ? <>{snap?.range_high_low} <span className="sub">{snap?.range_percent}</span></> : '—'}</div></div>
                  <div className="stat"><div className="label">52W Low</div><div className="value">{snap?.week_52_low ?? '—'}</div></div>
                  <div className="stat"><div className="label">52W High</div><div className="value">{snap?.week_52_high ?? '—'}</div></div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketDashboard;
