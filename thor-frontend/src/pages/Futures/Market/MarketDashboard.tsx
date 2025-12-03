import React, { useEffect, useMemo, useState } from "react";
// Market Open Session Styles are imported globally via src/styles/global.css

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
  ask_price?: string | null;
  ask_size?: number | null;
  bid_price?: string | null;
  bid_size?: number | null;
  volume?: number | null;
  market_open?: string | null;
  market_high_open?: string | null;
  market_high_pct_open?: string | null;
  market_low_open?: string | null;
  market_low_pct_open?: string | null;
  market_close?: string | null;
  market_high_pct_close?: string | null;
  market_low_pct_close?: string | null;
  market_close_vs_open_pct?: string | null;
  market_range?: string | null;
  market_range_pct?: string | null;
  spread?: string | null;
  prev_close_24h?: string | null;
  open_price_24h?: string | null;
  open_prev_diff_24h?: string | null;
  open_prev_pct_24h?: string | null;
  low_24h?: string | null;
  high_24h?: string | null;
  range_diff_24h?: string | null;
  range_pct_24h?: string | null;
  low_52w?: string | null;
  high_52w?: string | null;
  range_52w?: string | null;
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

type MarketLiveStatus = {
  next_event?: string;
  seconds_to_next_event?: number;
  current_state?: string;
  local_date_key?: string;
};

type IntradaySnapshot = {
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  volume?: number | null;
  spread?: number | null;
};

// Control markets must use exact country strings from backend sessions.
// Backend currently stores: Japan, China, India, Germany, United Kingdom, Pre_USA, USA, Canada, Mexico
const CONTROL_MARKETS = [
  { key: "Tokyo",       label: "Tokyo",        country: "Japan" },
  { key: "Shanghai",    label: "Shanghai",     country: "China" },
  { key: "Bombay",      label: "Bombay",       country: "India" },
  { key: "London",      label: "London",       country: "United Kingdom" }, // fixed backend country string
  { key: "Pre_USA",     label: "Pre-USA",      country: "Pre_USA" },
  { key: "USA",         label: "USA",          country: "USA" },
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

const parseNumericValue = (value?: string | number | null) => {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }
  const parsed = Number(String(value).replace(/,/g, ""));
  return Number.isNaN(parsed) ? null : parsed;
};

const formatSignedValue = (
  value?: string | number | null,
  { maxFrac = 2, showPlus = true }: { maxFrac?: number; showPlus?: boolean } = {}
) => {
  const parsed = parseNumericValue(value);
  if (parsed === null) return undefined;
  const formatted = parsed.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
  if (parsed > 0 && showPlus && !formatted.startsWith("+")) {
    return `+${formatted}`;
  }
  return formatted;
};

const formatPercentValue = (
  value?: string | number | null,
  options?: { maxFrac?: number; showPlus?: boolean }
) => {
  const formatted = formatSignedValue(value, { maxFrac: options?.maxFrac ?? 2, showPlus: options?.showPlus ?? true });
  return formatted ? `${formatted}%` : undefined;
};

const getDeltaClass = (value?: string | number | null) => {
  const parsed = parseNumericValue(value);
  if (parsed === null || parsed === 0) return "delta-neutral";
  return parsed > 0 ? "delta-positive" : "delta-negative";
};

// Helper to check if a value is zero (number or string)
const isZero = (v: any) => v === 0 || v === "0";

const formatNumOrDash = (value?: string | number | null, maxFrac = 2) => {
  const formatted = formatNum(value, maxFrac);
  if (formatted !== undefined) return formatted;
  return isZero(value) ? 0 : "—";
};

const buildDateKey = (year?: number | null, month?: number | null, day?: number | null) => {
  if (!year || !month || !day) return undefined;
  const paddedMonth = String(month).padStart(2, "0");
  const paddedDay = String(day).padStart(2, "0");
  return `${year}-${paddedMonth}-${paddedDay}`;
};

const getSessionDateKey = (session?: Pick<MarketOpenSession, "year" | "month" | "date"> | null) => {
  if (!session) return undefined;
  return buildDateKey(session.year, session.month, session.date);
};

// Allow API URLs to be set via environment variables or props, fallback to local dev endpoints
const getApiUrl = () => {
  return import.meta.env.VITE_MARKET_OPENS_API_URL || "http://127.0.0.1:8000/api/market-opens/latest/";
};

const getLiveStatusApiUrl = () => {
  return import.meta.env.VITE_GLOBAL_MARKETS_LIVE_STATUS_API_URL
    || "http://127.0.0.1:8000/api/global-markets/markets/live_status/";
};

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const getSessionApiUrl = () => {
  const explicit = import.meta.env.VITE_MARKET_SESSION_API_URL || import.meta.env.VITE_SESSION_API_URL;
  if (explicit) return trimTrailingSlash(explicit);
  const backendBase = import.meta.env.VITE_BACKEND_BASE_URL;
  if (backendBase) return `${trimTrailingSlash(backendBase)}/api/session`;
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${trimTrailingSlash(window.location.origin)}/api/session`;
  }
  return "http://127.0.0.1:8000/api/session";
};

const formatIntradayValue = (value?: number | null, maxFrac = 2) => {
  if (value === null || value === undefined) return "—";
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return "—";
  return parsed.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
};

const MarketDashboard: React.FC<{ apiUrl?: string }> = ({ apiUrl }) => {
  const resolvedApiUrl = apiUrl || getApiUrl();
  const resolvedLiveStatusUrl = getLiveStatusApiUrl();
  const sessionApiUrl = useMemo(() => getSessionApiUrl(), []);
  const [sessions, setSessions] = useState<MarketOpenSession[] | null>(null);
  const [liveStatus, setLiveStatus] = useState<Record<string, MarketLiveStatus>>({});
  const [intradayLatest, setIntradayLatest] = useState<Record<string, IntradaySnapshot | null>>({});

  // 🔹 Default future per market = TOTAL (per-country composite)
  const [selected, setSelected] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    CONTROL_MARKETS.forEach(m => {
      init[m.key] = "TOTAL";
    });
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
        const res = await fetch(resolvedLiveStatusUrl);
        if (!res.ok) {
          console.error("MarketDashboard: live status API error", res.status, res.statusText);
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
                seconds_to_next_event: typeof m.seconds_to_next_event === "number" ? m.seconds_to_next_event : undefined,
                current_state: m.current_state,
                local_date_key: localDateKey,
              };
            }
          }
        }
        if (!cancelled) setLiveStatus(map);
      } catch (e) {
        console.error("MarketDashboard: live status fetch failed", e);
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
  }, [resolvedApiUrl, resolvedLiveStatusUrl]);

  // Map dashboard key to backend session market_code
  const marketKeyToCode = (key: string) => {
    switch (key) {
      case "Tokyo": return "Tokyo";
      case "Bombay": return "India";
      case "London": return "London";
      case "Pre_USA": return "Pre_USA";
      case "USA": return "USA";
      default: return key; // fallback
    }
  };

  // Fetch intraday latest for each visible card and selected future (except TOTAL)
  useEffect(() => {
    let cancelled = false;

    async function loadIntraday() {
      const updates: Record<string, IntradaySnapshot | null> = {};
      await Promise.all(CONTROL_MARKETS.map(async (m) => {
        const sel = selected[m.key] || "TOTAL";
        if (sel === "TOTAL") return; // no intraday call for TOTAL composites
        const marketCode = marketKeyToCode(m.key);
        const url = `${sessionApiUrl}?market=${encodeURIComponent(marketCode)}&future=${encodeURIComponent(sel)}`;
        try {
          const res = await fetch(url);
          if (!res.ok) {
            updates[m.key] = null;
            return;
          }
          const data = await res.json();
          updates[m.key] = data?.intraday_latest || null;
        } catch (err) {
          console.error("MarketDashboard: intraday fetch failed", err);
          updates[m.key] = null;
        }
      }));
      if (!cancelled) setIntradayLatest(prev => ({ ...prev, ...updates }));
    }

    const id = setInterval(loadIntraday, 1000);
    loadIntraday();
    return () => { cancelled = true; clearInterval(id); };
  }, [selected, sessionApiUrl]);

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

          const sessionDateKey = latestRow ? getSessionDateKey(latestRow) : undefined;
          const marketDateKey = status?.local_date_key;
          let isPriorDay = false;
          if (sessionDateKey && marketDateKey) {
            isPriorDay = sessionDateKey !== marketDateKey;
          } else if (latestRow?.captured_at) {
            isPriorDay = !isToday(latestRow.captured_at);
          }
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
          const latestIntraday = intradayLatest[m.key];

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
          const closeDeltaValue = formatSignedValue(snap?.market_close);
          const closeDeltaPercent = formatPercentValue(snap?.market_close_vs_open_pct);
          const closeDeltaClass = getDeltaClass(
            snap?.market_close
              ?? snap?.market_close_vs_open_pct
              ?? snap?.market_high_pct_close
              ?? snap?.market_low_pct_close
          );
          const openDeltaMetric = {
            label: "Open Δ",
            primary: formatSignedValue(snap?.market_open),
            secondary: undefined,
            className: getDeltaClass(snap?.market_open),
          };
          const rangeColumnMetrics = [
            {
              label: "Low Δ",
              primary: formatSignedValue(snap?.market_low_open),
              secondary: formatPercentValue(snap?.market_low_pct_open),
              className: getDeltaClass(snap?.market_low_open ?? snap?.market_low_pct_open),
            },
            {
              label: "High Δ",
              primary: formatSignedValue(snap?.market_high_open),
              secondary: formatPercentValue(snap?.market_high_pct_open),
              className: getDeltaClass(snap?.market_high_open ?? snap?.market_high_pct_open),
            },
            {
              label: "Range Δ",
              primary: formatSignedValue(snap?.market_range),
              secondary: formatPercentValue(snap?.market_range_pct),
              className: getDeltaClass(snap?.market_range ?? snap?.market_range_pct),
            },
          ];
          const [lowMetric, highMetric, diffMetric] = rangeColumnMetrics;
          const showLowMetric = Boolean(lowMetric.primary || lowMetric.secondary);
          const showHighMetric = Boolean(highMetric.primary || highMetric.secondary);
          const showDiffMetric = Boolean(diffMetric.primary || diffMetric.secondary);
          const captureTime = snap?.captured_at ? new Date(snap.captured_at).toLocaleTimeString() : "—";
          const selectId = `future-select-${m.key}`;
          const bidPriceDisplay = formatNumOrDash(snap?.bid_price);
          const bidSizeDisplay = formatNumOrDash(snap?.bid_size, 0);
          const askPriceDisplay = formatNumOrDash(snap?.ask_price);
          const askSizeDisplay = formatNumOrDash(snap?.ask_size, 0);
          const openPrimary = openDeltaMetric.primary ?? "—";

          return (
            <div key={m.key} className="mo-rt-card">
              <div className="mo-rt-left">
                <div className="mo-rt-header">
                  <div className="mo-rt-header-chips">
                    <span className="chip sym">{m.label}</span>
                    <span className={chipClass("signal", signal || undefined)}>{signal || "—"}</span>
                    <span className={chipClass("status", outcomeStatus || undefined)}>{outcomeStatus || "—"}</span>
                    <span className="chip weight">Wgt: {snap?.weight ?? "—"}</span>
                    <span className="chip default">Capture {captureTime}</span>
                  </div>
                  <div className="mo-rt-header-select">
                    <label htmlFor={selectId} className="future-select-label">Future</label>
                    <select
                      id={selectId}
                      className="future-select"
                      value={selectedSymbol}
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
                        <div className={`val ${closeDeltaClass}`}>
                          {closeDeltaValue ?? (isZero(snap?.market_close) ? "0" : "—")}
                        </div>
                        <div className={`pct ${closeDeltaClass}`}>
                            {closeDeltaPercent
                              ?? (isZero(snap?.market_close_vs_open_pct) ? "0%" : "—")}
                        </div>
                        <div className="label">Close Δ</div>
                      </div>
                    </div>

                    <div className="mo-rt-deltas">
                      <div className="delta-column">
                        <div className="delta-card bbo-card">
                          <div className="bbo-section">
                            <div className="bbo-head bid">Bid</div>
                            <div className="bbo-main">{bidPriceDisplay}</div>
                            <div className="bbo-sub">Size {bidSizeDisplay}</div>
                          </div>
                          <div className="bbo-divider" aria-hidden="true" />
                          <div className="bbo-section">
                            <div className="bbo-head ask">Ask</div>
                            <div className="bbo-main">{askPriceDisplay}</div>
                            <div className="bbo-sub">Size {askSizeDisplay}</div>
                          </div>
                        </div>
                      </div>
                      {(openPrimary || showLowMetric || showHighMetric || showDiffMetric) && (
                        <div className="delta-column">
                          <div className="delta-row">
                            <div className="delta-card" key="open-metric">
                              <div className="delta-label">{openDeltaMetric.label}</div>
                              <div className={`delta-value ${openDeltaMetric.className}`}>
                                {openPrimary}
                              </div>
                              {openDeltaMetric.secondary && (
                                <div className="delta-sub">{openDeltaMetric.secondary}</div>
                              )}
                            </div>
                            {showLowMetric && (
                              <div className="delta-card" key="low-metric">
                                <div className="delta-label">{lowMetric.label}</div>
                                <div className={`delta-value ${lowMetric.className}`}>
                                  {lowMetric.primary ?? "—"}
                                </div>
                                {lowMetric.secondary && (
                                  <div className="delta-sub">{lowMetric.secondary}</div>
                                )}
                              </div>
                            )}
                            {showHighMetric && (
                              <div className="delta-card" key="high-metric">
                                <div className="delta-label">{highMetric.label}</div>
                                <div className={`delta-value ${highMetric.className}`}>
                                  {highMetric.primary ?? "—"}
                                </div>
                                {highMetric.secondary && (
                                  <div className="delta-sub">{highMetric.secondary}</div>
                                )}
                              </div>
                            )}
                          </div>
                          {showDiffMetric && (
                            <div className="delta-card" key="range-metric">
                              <div className="delta-label">{diffMetric.label}</div>
                              <div className={`delta-value ${diffMetric.className}`}>
                                {diffMetric.primary ?? "—"}
                              </div>
                              {diffMetric.secondary && (
                                <div className="delta-sub">{diffMetric.secondary}</div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="mo-rt-meta">
                      <div className="meta">
                        <div className="meta-label">Entry</div>
                        <div className="meta-value">{formatNum(snap?.entry_price) ?? (isZero(snap?.entry_price) ? 0 : "—")}</div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {!isTotalFuture && (
                <div className="mo-rt-right">
                  <div className="mo-rt-right-columns">
                    <div className="session-stats-column">
                      <div className="mo-rt-stats-title">Session Stats</div>
                      <div className="mo-rt-stats">
                        <div className="stat">
                          <div className="stat-label">Volume</div>
                          <div className="stat-value">{snap?.volume !== undefined && snap?.volume !== null ? formatNum(snap?.volume, 0) : "—"}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">Prev Close (24h)</div>
                          <div className="stat-value">{formatNum(snap?.prev_close_24h) ?? (isZero(snap?.prev_close_24h) ? 0 : "—")}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">Open (24h)</div>
                          <div className="stat-value">{formatNum(snap?.open_price_24h) ?? (isZero(snap?.open_price_24h) ? 0 : "—")}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">24h Low</div>
                          <div className="stat-value">{formatNum(snap?.low_24h) ?? (isZero(snap?.low_24h) ? 0 : "—")}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">24h High</div>
                          <div className="stat-value">{formatNum(snap?.high_24h) ?? (isZero(snap?.high_24h) ? 0 : "—")}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">24h Range</div>
                          <div className="stat-value">{snap?.range_diff_24h ? `${formatNum(snap?.range_diff_24h)} (${formatNum(snap?.range_pct_24h) ?? "—"})` : "—"}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">52W Low</div>
                          <div className="stat-value">{formatNum(snap?.low_52w) ?? (isZero(snap?.low_52w) ? 0 : "—")}</div>
                        </div>
                        <div className="stat">
                          <div className="stat-label">52W High</div>
                          <div className="stat-value">{formatNum(snap?.high_52w) ?? (isZero(snap?.high_52w) ? 0 : "—")}</div>
                        </div>
                      </div>
                    </div>
                    <div className="intraday-column">
                      <div className="intraday-title">Intraday 1m</div>
                      <div className="intraday-grid">
                        {[{
                          key: "open",
                          label: "Open",
                          value: formatIntradayValue(latestIntraday?.open),
                        }, {
                          key: "low",
                          label: "Low",
                          value: formatIntradayValue(latestIntraday?.low),
                        }, {
                          key: "high",
                          label: "High",
                          value: formatIntradayValue(latestIntraday?.high),
                        }, {
                          key: "close",
                          label: "Close",
                          value: formatIntradayValue(latestIntraday?.close),
                        }, {
                          key: "volume",
                          label: "Volume",
                          value: formatIntradayValue(latestIntraday?.volume, 0),
                        }, {
                          key: "spread",
                          label: "Spread",
                          value: formatIntradayValue(latestIntraday?.spread, 3),
                        }].map(item => (
                          <div className="intraday-card" key={item.key}>
                            <div className="intraday-label">{item.label}</div>
                            <div className="intraday-value">{item.value}</div>
                          </div>
                        ))}
                      </div>
                      {!latestIntraday && (
                        <div className="intraday-empty">Waiting for live data...</div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketDashboard;
