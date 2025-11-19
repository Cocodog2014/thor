import React, { useEffect, useMemo, useState } from "react";
// Styles are imported globally via src/styles/global.css

// ---- Types ----
// Single-table design: each row represents one future at one market open
interface MarketOpenSession {
  id: number;
  session_number: number;
  year: number;
  month: number;
  date: number;
  day: string;
  captured_at: string;
  country: string;
  future: string; // YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB, TOTAL
  country_future?: string | null;
  weight?: number | null;
  last_price?: string | null;
  change?: string | null;
  change_percent?: string | null;
  reference_ask?: string | null;
  ask_size?: number | null;
  reference_bid?: string | null;
  bid_size?: number | null;
  volume?: number | null;
  vwap?: string | null;
  spread?: string | null;
  reference_close?: string | null;
  reference_open?: string | null;
  day_24h_low?: string | null;
  day_24h_high?: string | null;
  range_high_low?: string | null;
  range_percent?: string | null;
  week_52_low?: string | null;
  week_52_high?: string | null;
  entry_price?: string | null;
  target_high?: string | null;
  target_low?: string | null;
  weighted_average?: string | null;
  bhs?: string | null;
  instrument_count?: number | null;
  outcome?: string | null;
  fw_nwdw?: string | null;
  exit_price?: string | null;
  fw_exit_value?: string | null;
  fw_exit_percent?: string | null;
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

const formatNum = (n?: string | number | null, maxFrac = 2) => {
  if (n === null || n === undefined || n === "") return undefined;
  if (typeof n === "number") {
    return n.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
  }
  const s = String(n);
  const p = Number(s.replace(/,/g, ""));
  if (Number.isNaN(p)) return s;
  return p.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
};

// Helper to check if a value is zero (number or string)
const isZero = (v: any) => v === 0 || v === "0";


// Allow API URL to be set via environment variable or prop, fallback to relative path
const getApiUrl = () => {
  // Vite env vars must start with VITE_
  // Example: VITE_MARKET_OPENS_API_URL=https://thor.360edu.org/api/market-opens/latest/
  // Default to local Django server on port 8000 for dev
  return import.meta.env.VITE_MARKET_OPENS_API_URL || 'http://127.0.0.1:8000/api/market-opens/latest/';
};

const MarketDashboard: React.FC<{ apiUrl?: string }> = ({ apiUrl }) => {
  const resolvedApiUrl = apiUrl || getApiUrl();
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
        const res = await fetch(resolvedApiUrl);
        if (!res.ok) {
          console.error('MarketDashboard: API error', res.status, res.statusText);
          if (!cancelled) setSessions([]);
          return;
        }
        const data = await res.json();
        if (!cancelled) setSessions(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error('MarketDashboard: fetch failed', e);
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
  }, [resolvedApiUrl]);

  // Helper to normalize country names for robust matching
    const normalizeCountry = (c?: string) => (c || "").trim().toLowerCase();

    // Map backend sessions by normalized country
    const byCountry = useMemo(() => {
      const map = new Map<string, MarketOpenSession[]>();
      (sessions || []).forEach(s => {
        const countryKey = normalizeCountry(s.country);
        if (!map.has(countryKey)) map.set(countryKey, []);
        map.get(countryKey)!.push(s);
      });
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
    // Find TOTAL row from any country (most recent)
    const allRows = (sessions || []).filter(s => s.future === 'TOTAL').sort((a, b) =>
      new Date(b.captured_at).getTime() - new Date(a.captured_at).getTime()  
    );
    
    if (allRows.length > 0) {
      return allRows[0]; // Return the TOTAL row directly
    }
    return null;
  }, [byCountry]);

  return (
    <div className="market-dashboard">
      <div className="market-dashboard-header">
        <h3 className="market-open-header-title">📊 Market Open Sessions</h3>
        <div className="text-xs subtitle-text">Always shows all 9 control markets</div>
      </div>

      {/* TOTAL Composite Card - always show, spans 3 columns */}
      <div className="total-composite-card">
        <div className="total-header">
          <span className="total-title">TOTAL</span>
          <span className="total-badge composite">Composite</span>
          <span className="total-badge futures">11 Futures</span>
          {totalSession && (
            <span
              className={`total-pill ${String(totalSession.bhs || '').toLowerCase().replace('_','-')}`}
            >
              {(totalSession.bhs || '—').replace('_',' ')}
            </span>
          )}
          <span className="total-time">
            {totalSession?.captured_at ? new Date(totalSession.captured_at).toLocaleTimeString() : "—"}
          </span>
        </div>
        {totalSession ? (
          <div className="total-body">
            <div className="total-left">
              <div className="total-val">{formatNum(String(totalSession.weighted_average), 3) || '—'}</div>
              <div className="total-label">Weighted Average</div>
              <div className="total-left-metrics">
                <div className="total-mini-card">
                  <div className="mini-title">Count</div>
                  <div className="mini-value">{totalSession.instrument_count ?? '—'}</div>
                  <div className="mini-sub">Instruments</div>
                </div>
                <div className="total-mini-card">
                  <div className="mini-title">Weight</div>
                  <div className="mini-value">{totalSession.weight ?? '—'}</div>
                  <div className="mini-sub">Composite</div>
                </div>
              </div>
            </div>
            <div className="total-right">
              <div className="live-label">LIVE TOTAL</div>
            </div>
          </div>
        ) : (
          <div className="total-empty">🪫 No TOTAL data captured yet — waiting for market open…</div>
        )}
      </div>

      <div className="market-grid">
        {CONTROL_MARKETS.map(m => {
          const countryKey = normalizeCountry(m.country);
          const rows = byCountry.get(countryKey) || [];
          // Find the latest captured_at across all futures for this market
          const latestRow = rows.length > 0 ? rows.reduce((latest, r) => 
            new Date(r.captured_at) > new Date(latest.captured_at) ? r : latest
          ) : null;

          const status = liveStatus[m.country];
          const seconds = status?.seconds_to_next_event ?? undefined;
          const nextEvent = status?.next_event;

          // Keep prior day's card visible until 5 minutes (300s) before today's open
          const isPriorDay = latestRow?.captured_at ? !isToday(latestRow.captured_at) : false;
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
          const time = latestRow?.captured_at ? new Date(latestRow.captured_at).toLocaleTimeString() : "—";

          const selectedSymbol = selected[m.key];
          // Find the row for the selected future
          const snap = rows.find(r => r.future?.toUpperCase() === selectedSymbol?.toUpperCase()) || rows[0];

          const signal = snap?.bhs;
          const outcomeStatus = snap?.fw_nwdw;

          return (
            <div key={m.key} className="mo-rt-card">
              <div className="mo-rt-header">
                <span className="mo-rt-chip sym">{m.label}</span>
                <span className={chipClass("signal", signal || undefined)}>{signal || "—"}</span>
                <span className={chipClass("status", outcomeStatus || undefined)}>{outcomeStatus || "—"}</span>
                <span className="mo-rt-chip">Wgt: {snap?.weight ?? '—'}</span>
                <span className="mo-rt-time">{time}</span>
              </div>

              <div className="mo-rt-body">
                {/* Chips + Future Dropdown */}
                <div className="flex-controls">
                  <div className="ml-auto">
                    <label className="future-select-label">Future</label>
                    <select
                      className="future-select"
                      value={selected[m.key]}
                      onChange={(e) => setSelected(prev => ({ ...prev, [m.key]: e.target.value }))}
                      aria-label="Select future contract"
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
                    <div className="val">{formatNum(snap?.last_price) ?? (isZero(snap?.last_price) ? 0 : '—')}</div>
                    <div className="label">Last</div>
                  </div>
                  <div className="mo-rt-change">
                    <div className="val">{formatNum(snap?.change) ?? (isZero(snap?.change) ? 0 : '—')}</div>
                    <div className="pct">{formatNum(snap?.change_percent, 2) ?? (isZero(snap?.change_percent) ? 0 : '—')}%</div>
                    <div className="label">Change</div>
                  </div>
                </div>

                {/* BBO tiles */}
                <div className="mo-rt-bbo">
                  <div className="tile bid">
                    <div className="t-head">BID</div>
                    <div className="t-main">{formatNum(snap?.reference_bid) ?? (isZero(snap?.reference_bid) ? 0 : '—')}</div>
                    <div className="t-sub">Size {formatNum(snap?.bid_size, 0) ?? (isZero(snap?.bid_size) ? 0 : '—')}</div>
                  </div>
                  <div className="tile ask">
                    <div className="t-head">ASK</div>
                    <div className="t-main">{formatNum(snap?.reference_ask) ?? (isZero(snap?.reference_ask) ? 0 : '—')}</div>
                    <div className="t-sub">Size {formatNum(snap?.ask_size, 0) ?? (isZero(snap?.ask_size) ? 0 : '—')}</div>
                  </div>
                </div>

                {/* Stats grid */}
                <div className="mo-rt-stats">
                  <div className="stat"><div className="label">Volume</div><div className="value">{snap?.volume !== undefined && snap?.volume !== null ? formatNum(snap?.volume, 0) : '—'}</div></div>
                  <div className="stat"><div className="label">VWAP</div><div className="value">{formatNum(snap?.vwap) ?? (isZero(snap?.vwap) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">Close</div><div className="value">{formatNum(snap?.reference_close) ?? (isZero(snap?.reference_close) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">Open</div><div className="value">{formatNum(snap?.reference_open) ?? (isZero(snap?.reference_open) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">24h Low</div><div className="value">{formatNum(snap?.day_24h_low) ?? (isZero(snap?.day_24h_low) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">24h High</div><div className="value">{formatNum(snap?.day_24h_high) ?? (isZero(snap?.day_24h_high) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">24h Range</div><div className="value">{snap?.range_high_low ? <>{formatNum(snap?.range_high_low)} <span className="sub">{formatNum(snap?.range_percent)}</span></> : '—'}</div></div>
                  <div className="stat"><div className="label">52W Low</div><div className="value">{formatNum(snap?.week_52_low) ?? (isZero(snap?.week_52_low) ? 0 : '—')}</div></div>
                  <div className="stat"><div className="label">52W High</div><div className="value">{formatNum(snap?.week_52_high) ?? (isZero(snap?.week_52_high) ? 0 : '—')}</div></div>
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
