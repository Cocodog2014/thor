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
  country_future_wndw_total?: string | null;
  weight?: number | null;
  last_price?: string | null;
  change?: string | null;
  change_percent?: string | null;
  ask_price?: string | null;
  ask_size?: number | null;
  bid_price?: string | null;
  bid_size?: number | null;
  volume?: number | null;
  vwap?: string | null;
  spread?: string | null;
  session_close?: string | null;
  session_open?: string | null;
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
  wndw?: string | null;
  exit_price?: string | null;
  fw_exit_value?: string | null;
  fw_exit_percent?: string | null;
}

const CONTROL_MARKETS = [
  { key: "Tokyo", label: "Tokyo", country: "Japan" },
  { key: "Shanghai", label: "Shanghai", country: "China" },
  { key: "Bombay", label: "Bombay", country: "India" },
  { key: "Frankfurt", label: "Frankfurt", country: "Germany" },
  { key: "London", label: "London", country: "United Kingdom" },
  { key: "Pre_USA", label: "Pre_USA", country: "Pre_USA" },
  { key: "USA", label: "USA", country: "USA" },
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
  const classes = ["chip", kind];
  const v = (value || "").toUpperCase();
  if (!value) {
    classes.push("default");
    return classes.join(" ");
  }
  if (kind === "signal") {
    if (v === "BUY" || v === "STRONG_BUY") classes.push("success");
    else if (v === "SELL" || v === "STRONG_SELL") classes.push("error");
    else if (v === "HOLD") classes.push("warning");
    else classes.push("default");
  } else {
    if (v === "WORKED") classes.push("success");
    else if (v === "DIDNT_WORK") classes.push("error");
    else if (v === "PENDING") classes.push("warning");
    else classes.push("default");
  }
  return classes.join(" ");
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
  return import.meta.env.VITE_MARKET_OPENS_API_URL || "http://127.0.0.1:8000/api/market-opens/latest/";
};

const MarketDashboard: React.FC<{ apiUrl?: string }> = ({ apiUrl }) => {
  const resolvedApiUrl = apiUrl || getApiUrl();
  const [sessions, setSessions] = useState<MarketOpenSession[] | null>(null);
  const [liveStatus, setLiveStatus] = useState<Record<string, { next_event?: string; seconds_to_next_event?: number }>>({});

  // 🔹 Default future per market = TOTAL (per-country composite)
  const [selected, setSelected] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    CONTROL_MARKETS.forEach(m => { init[m.key] = "TOTAL"; });
    return init;
  });

  useEffect(() => {
    let cancelled = false;
    let running = false;

    async function loadSessions() {
      try {
        const res = await fetch(resolvedApiUrl);
        if (!res.ok) {
          console.error("MarketDashboard: API error", res.status, res.statusText);
          if (!cancelled) setSessions([]);
          return;
        }
        const data = await res.json();
        if (!cancelled) setSessions(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error("MarketDashboard: fetch failed", e);
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
                seconds_to_next_event: typeof m.seconds_to_next_event === "number" ? m.seconds_to_next_event : undefined,
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
    const id = setInterval(tick, 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [resolvedApiUrl]);

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

  return (
    <div className="market-dashboard">
      <div className="market-dashboard-header">
        <h3 className="market-open-header-title">📊 Market Open Sessions</h3>
        <div className="text-xs subtitle-text">Shows all control markets with their own TOTAL</div>
      </div>

      {/* 🔸 No global TOTAL — each market card handles its own TOTAL via the dropdown */}

      <div className="market-grid">
        {CONTROL_MARKETS.map(m => {
          const countryKey = normalizeCountry(m.country);
          const rows = byCountry.get(countryKey) || [];

          const latestRow = rows.length > 0 ? rows.reduce((latest, r) =>
            new Date(r.captured_at) > new Date(latest.captured_at) ? r : latest
          ) : null;

          const status = liveStatus[m.country];
          const seconds = status?.seconds_to_next_event ?? undefined;
          const nextEvent = status?.next_event;

          const isPriorDay = latestRow?.captured_at ? !isToday(latestRow.captured_at) : false;
          const hidePriorNow = isPriorDay && nextEvent === "open" && typeof seconds === "number" && seconds <= 300;
          if (hidePriorNow) {
            return (
              <div key={m.key} className="mo-rt-card">
                <div className="mo-rt-left">
                  <div className="mo-rt-header">
                    <div className="mo-rt-header-chips">
                      <span className="chip sym">{m.label}</span>
                      <span className="chip default">Awaiting market open…</span>
                    </div>
                  </div>
                  <div className="mo-rt-placeholder">Prior capture hidden 5 minutes before today&apos;s open.</div>
                </div>
              </div>
            );
          }

          const defaultFuture = "TOTAL"; // per-country composite as default
          const selectedSymbol = selected[m.key] || defaultFuture;

          const snap = rows.find(r => r.future?.toUpperCase() === selectedSymbol.toUpperCase()) || rows[0];

          if (!snap) {
            return (
              <div key={m.key} className="mo-rt-card">
                <div className="mo-rt-left">
                  <div className="mo-rt-header">
                    <div className="mo-rt-header-chips">
                      <span className="chip sym">{m.label}</span>
                      <span className="chip default">No capture yet</span>
                    </div>
                  </div>
                  <div className="mo-rt-placeholder">No market capture has been recorded for this session yet.</div>
                </div>
              </div>
            );
          }

          const signal = snap?.bhs;
          const outcomeStatus = snap?.wndw;
          const isTotalFuture = (snap.future || "").toUpperCase() === "TOTAL";
          const totalSumRaw = snap.country_future_wndw_total ?? snap.country_future;
          const totalWeightedAverage = formatNum(snap?.weighted_average, 3) ?? (isZero(snap?.weighted_average) ? 0 : "—");
          const totalSumValue = formatNum(totalSumRaw) ?? (isZero(totalSumRaw) ? 0 : "—");
          const totalInstrumentCount = snap?.instrument_count ?? 11;
          const totalCapture = snap?.captured_at ? new Date(snap.captured_at).toLocaleTimeString() : "—";

          return (
            <div key={m.key} className="mo-rt-card">
              <div className="mo-rt-left">
                <div className="mo-rt-header">
                  <div className="mo-rt-header-chips">
                    <span className="chip sym">{m.label}</span>
                    {!isTotalFuture && (
                      <span className={chipClass("signal", signal || undefined)}>{signal || "—"}</span>
                    )}
                    <span className={chipClass("status", outcomeStatus || undefined)}>{outcomeStatus || "—"}</span>
                    {!isTotalFuture && (
                      <span className="chip weight">Wgt: {snap?.weight ?? "—"}</span>
                    )}
                  </div>
                  <div>
                    <span className="future-select-label">Future</span>
                    <select
                      className="future-select"
                      value={selected[m.key] || defaultFuture}
                      onChange={(e) => setSelected(prev => ({ ...prev, [m.key]: e.target.value }))}
                      aria-label="Select future contract"
                    >
                      {FUTURE_OPTIONS.map(o => (
                        <option key={o.key} value={o.key}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {isTotalFuture ? (
                  <div className="total-inline-card">
                    <div className="total-inline-top">
                      <div>
                        <div className="total-inline-title">TOTAL</div>
                        <div className="total-inline-tags">
                          <span className="total-inline-badge">Composite</span>
                          <span className="total-inline-badge">{totalInstrumentCount} Futures</span>
                        </div>
                      </div>
                      <div className="total-inline-signal">
                        <span className={chipClass("signal", signal || undefined)}>{signal || "—"}</span>
                        <span className="total-inline-weight">Wgt: {snap?.weight ?? "—"}</span>
                      </div>
                    </div>
                    <div className="total-inline-main">
                      <div className="total-inline-value">{totalWeightedAverage}</div>
                      <div className="total-inline-label">Weighted Average</div>
                    </div>
                    <div className="total-inline-metrics">
                      <div className="total-inline-mini">
                        <div className="mini-title">Sum</div>
                        <div className="mini-value">{totalSumValue}</div>
                        <div className="mini-sub">Weighted</div>
                      </div>
                      <div className="total-inline-mini">
                        <div className="mini-title">Count</div>
                        <div className="mini-value">{totalInstrumentCount}</div>
                        <div className="mini-sub">Instruments</div>
                      </div>
                    </div>
                    <div className="total-inline-meta">
                      <span>Capture: {totalCapture}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mo-rt-top">
                      <div className="mo-rt-last">
                        <div className="val">{formatNum(snap?.last_price) ?? (isZero(snap?.last_price) ? 0 : "—")}</div>
                        <div className="label">Last</div>
                      </div>
                      <div className="mo-rt-change">
                        <div className="val">{formatNum(snap?.change) ?? (isZero(snap?.change) ? 0 : "—")}</div>
                        <div className="pct">{formatNum(snap?.change_percent, 2) ?? (isZero(snap?.change_percent) ? 0 : "—")}%</div>
                        <div className="label">Change</div>
                      </div>
                    </div>

                    <div className="mo-rt-bbo">
                      <div className="bbo-tile">
                        <div className="bbo-head bid">Bid</div>
                        <div className="bbo-main">{formatNum(snap?.bid_price) ?? (isZero(snap?.bid_price) ? 0 : "—")}</div>
                        <div className="bbo-sub">Size {formatNum(snap?.bid_size, 0) ?? (isZero(snap?.bid_size) ? 0 : "—")}</div>
                      </div>
                      <div className="bbo-tile">
                        <div className="bbo-head ask">Ask</div>
                        <div className="bbo-main">{formatNum(snap?.ask_price) ?? (isZero(snap?.ask_price) ? 0 : "—")}</div>
                        <div className="bbo-sub">Size {formatNum(snap?.ask_size, 0) ?? (isZero(snap?.ask_size) ? 0 : "—")}</div>
                      </div>
                    </div>

                    <div className="mo-rt-meta">
                      <div className="meta">
                        <div className="meta-label">Capture</div>
                        <div className="meta-value">{snap?.captured_at ? new Date(snap.captured_at).toLocaleTimeString() : "—"}</div>
                      </div>
                      <div className="meta">
                        <div className="meta-label">Contract</div>
                        <div className="meta-value">{snap?.future || "—"}</div>
                      </div>
                      <div className="meta">
                        <div className="meta-label">Entry</div>
                        <div className="meta-value">{formatNum(snap?.entry_price) ?? (isZero(snap?.entry_price) ? 0 : "—")}</div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="mo-rt-right">
                <div className="mo-rt-stats-title">Session Stats</div>
                <div className="mo-rt-stats">
                  <div className="stat">
                    <div className="stat-label">Volume</div>
                    <div className="stat-value">{snap?.volume !== undefined && snap?.volume !== null ? formatNum(snap?.volume, 0) : "—"}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">VWAP</div>
                    <div className="stat-value">{formatNum(snap?.vwap) ?? (isZero(snap?.vwap) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">Close</div>
                    <div className="stat-value">{formatNum(snap?.session_close) ?? (isZero(snap?.session_close) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">Open</div>
                    <div className="stat-value">{formatNum(snap?.session_open) ?? (isZero(snap?.session_open) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">24h Low</div>
                    <div className="stat-value">{formatNum(snap?.day_24h_low) ?? (isZero(snap?.day_24h_low) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">24h High</div>
                    <div className="stat-value">{formatNum(snap?.day_24h_high) ?? (isZero(snap?.day_24h_high) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">24h Range</div>
                    <div className="stat-value">{snap?.range_high_low ? `${formatNum(snap?.range_high_low)} (${formatNum(snap?.range_percent) ?? "—"})` : "—"}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">52W Low</div>
                    <div className="stat-value">{formatNum(snap?.week_52_low) ?? (isZero(snap?.week_52_low) ? 0 : "—")}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">52W High</div>
                    <div className="stat-value">{formatNum(snap?.week_52_high) ?? (isZero(snap?.week_52_high) ? 0 : "—")}</div>
                  </div>
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
