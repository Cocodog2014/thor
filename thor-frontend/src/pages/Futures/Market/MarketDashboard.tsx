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

// Demo fallback rows so UI can render when API has no data
const DEMO_SESSIONS: MarketOpenSession[] = [
  {
    id: 1,
    session_number: 12,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "Japan",
    future: "TOTAL",
    country_future: "126.40",
    country_future_wndw_total: "126.40",
    weight: 1.0,
    last_price: "4532.75",
    ask_price: "4533.00",
    ask_size: 12,
    bid_price: "4532.50",
    bid_size: 10,
    volume: 1240000,
    market_open: "-0.28",
    market_high_open: "+15.50",
    market_high_pct_open: "+0.51",
    market_low_open: "-23.50",
    market_low_pct_open: "-0.51",
    market_close: "+15.25",
    market_high_pct_close: "+0.34",
    market_low_pct_close: null,
    market_close_vs_open_pct: "+0.34",
    market_range: "35.25",
    market_range_pct: "0.78",
    spread: "0.25",
    prev_close_24h: "4517.50",
    open_price_24h: "4520.00",
    open_prev_diff_24h: "+2.50",
    open_prev_pct_24h: "+0.06",
    low_24h: "4510.25",
    high_24h: "4545.50",
    range_diff_24h: "35.25",
    range_pct_24h: "0.78",
    low_52w: "4000.00",
    high_52w: "4800.00",
    range_52w: "800.00",
    entry_price: "4520.00",
    target_high: "4540.00",
    target_low: "4510.00",
    weighted_average: "126.40",
    bhs: "BUY",
    instrument_count: 11,
    outcome: "WORKED",
    wndw: "WORKED",
    exit_price: "4532.75",
    fw_exit_value: "+15.25",
    fw_exit_percent: "+0.34",
  },
  {
    id: 2,
    session_number: 8,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "China",
    future: "TOTAL",
    country_future: "113.20",
    country_future_wndw_total: "113.20",
    weight: 1.0,
    last_price: "3456.10",
    ask_price: "3456.30",
    ask_size: 9,
    bid_price: "3455.90",
    bid_size: 8,
    volume: 820000,
    market_open: "-0.12",
    market_high_open: "+10.05",
    market_high_pct_open: "+0.29",
    market_low_open: "-14.20",
    market_low_pct_open: "-0.41",
    market_close: "-2.25",
    market_close_vs_open_pct: "-0.06",
    market_range: "24.25",
    market_range_pct: "0.70",
    weighted_average: "113.20",
    bhs: "NEUTRAL",
    instrument_count: 11,
    outcome: "MISSED",
    wndw: "DIDNT_WORK",
  },
  {
    id: 3,
    session_number: 10,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "India",
    future: "TOTAL",
    country_future: "98.75",
    country_future_wndw_total: "98.75",
    weight: 1.0,
    last_price: "2899.50",
    market_open: "+1.25",
    market_close: "+3.50",
    market_close_vs_open_pct: "+0.12",
    weighted_average: "98.75",
    bhs: "SELL",
    instrument_count: 11,
    outcome: "WORKED",
    wndw: "WORKED",
  },
  {
    id: 4,
    session_number: 9,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "United Kingdom",
    future: "TOTAL",
    country_future: "121.05",
    country_future_wndw_total: "121.05",
    weight: 1.0,
    last_price: "7550.25",
    market_open: "+0.75",
    market_close: "+2.15",
    market_close_vs_open_pct: "+0.09",
    weighted_average: "121.05",
    bhs: "BUY",
    instrument_count: 11,
    outcome: "WORKED",
    wndw: "WORKED",
  },
  {
    id: 5,
    session_number: 1,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "Pre_USA",
    future: "TOTAL",
    country_future: "110.00",
    country_future_wndw_total: "110.00",
    weight: 1.0,
    last_price: "4599.00",
    market_open: "0.00",
    market_close: "0.00",
    market_close_vs_open_pct: "0.00",
    weighted_average: "110.00",
    bhs: "NEUTRAL",
    instrument_count: 11,
    outcome: "PENDING",
    wndw: "PENDING",
  },
  {
    id: 6,
    session_number: 2,
    year: 2025,
    month: 12,
    date: 3,
    day: "Wed",
    captured_at: new Date().toISOString(),
    country: "USA",
    future: "TOTAL",
    country_future: "130.25",
    country_future_wndw_total: "130.25",
    weight: 1.0,
    last_price: "4732.75",
    market_open: "+2.25",
    market_close: "+15.25",
    market_close_vs_open_pct: "+0.34",
    weighted_average: "130.25",
    bhs: "BUY",
    instrument_count: 11,
    outcome: "LIVE",
    wndw: "PENDING",
  },
];

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

const getTriangleClass = (value?: string | number | null) => {
  const deltaClass = getDeltaClass(value);
  if (deltaClass === "delta-positive") return "triangle-up";
  if (deltaClass === "delta-negative") return "triangle-down";
  return "triangle-neutral";
};

const buildPercentCell = (value?: string | number | null, fallback = "—") => {
  return {
    text: formatPercentValue(value) ?? fallback,
    className: getDeltaClass(value),
  };
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
        if (!cancelled) {
          const list = Array.isArray(data) ? data : [];
          setSessions(list.length > 0 ? list : DEMO_SESSIONS);
        }
      } catch (e) {
        console.error("MarketDashboard: fetch failed", e);
        if (!cancelled) setSessions(DEMO_SESSIONS);
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
        if (!cancelled) {
          // Seed demo live status when API empty
          const withDemo = Object.keys(map).length > 0 ? map : {
            Japan: { next_event: "close", seconds_to_next_event: 120, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
            China: { next_event: "open", seconds_to_next_event: 3600, current_state: "CLOSED", local_date_key: buildDateKey(2025,12,3) },
            India: { next_event: "close", seconds_to_next_event: 600, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
            "United Kingdom": { next_event: "close", seconds_to_next_event: 1800, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
            Pre_USA: { next_event: "open", seconds_to_next_event: 900, current_state: "PREOPEN", local_date_key: buildDateKey(2025,12,3) },
            USA: { next_event: "close", seconds_to_next_event: 14400, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
          };
          setLiveStatus(withDemo);
        }
      } catch (e) {
        console.error("MarketDashboard: live status fetch failed", e);
        if (!cancelled) setLiveStatus({
          Japan: { next_event: "close", seconds_to_next_event: 120, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
          China: { next_event: "open", seconds_to_next_event: 3600, current_state: "CLOSED", local_date_key: buildDateKey(2025,12,3) },
          India: { next_event: "close", seconds_to_next_event: 600, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
          "United Kingdom": { next_event: "close", seconds_to_next_event: 1800, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
          Pre_USA: { next_event: "open", seconds_to_next_event: 900, current_state: "PREOPEN", local_date_key: buildDateKey(2025,12,3) },
          USA: { next_event: "close", seconds_to_next_event: 14400, current_state: "OPEN", local_date_key: buildDateKey(2025,12,3) },
        });
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
      {/* Inline styles for MarketDashboard (kept local per request) */}
      <style>{`
        .market-dashboard { width: 100%; padding: 16px; }
        .market-dashboard-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; }
        .market-open-header-title { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
        .subtitle-text { opacity: 0.75; }

        .market-grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
        .mo-rt-card { background: #1e1e1e; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); padding: 14px 16px; display: flex; gap: 12px; }
        .mo-rt-left { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
        .mo-rt-right { flex: 0 0 auto; min-width: 280px; }

        .mo-rt-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
        .mo-rt-header-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
        .chip { padding: 3px 8px; border-radius: 999px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; background: rgba(255,255,255,0.08); }
        .chip.sym { background: rgba(255,255,255,0.15); }
        .chip.weight { background: rgba(0,0,0,0.4); }
        .chip.default { background: rgba(148,163,184,0.35); }
        .chip.signal.success { background: rgba(16,185,129,0.35); }
        .chip.signal.error { background: rgba(239,68,68,0.35); }
        .chip.signal.warning { background: rgba(255,193,7,0.35); }
        .chip.status.success { background: rgba(16,185,129,0.35); }
        .chip.status.error { background: rgba(239,68,68,0.35); }
        .chip.status.warning { background: rgba(255,193,7,0.35); }

        .mo-rt-header-select { display: flex; align-items: center; gap: 6px; font-size: 11px; }
        .future-select-label { font-size: 11px; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.05em; }
        .future-select { background: rgba(0,0,0,0.5); border-radius: 6px; border: 1px solid rgba(255,255,255,0.2); padding: 3px 8px; color: #fff; font-size: 12px; }

        .mo-rt-top { display: grid; grid-template-columns: minmax(0, 1fr) 140px; gap: 12px; }
        .mo-rt-last .val { font-size: 28px; font-weight: 800; line-height: 1; }
        .mo-rt-last .label { font-size: 12px; opacity: 0.75; }
        .mo-rt-change { text-align: right; }
        .mo-rt-change .val { font-size: 16px; font-weight: 700; }
        .mo-rt-change .pct { font-size: 13px; font-weight: 600; }
        .mo-rt-change .label { font-size: 12px; opacity: 0.75; }
        .delta-positive { color: #5cc569; }
        .delta-negative { color: #f26d6d; }
        .delta-neutral { color: #fff; opacity: 0.85; }

        .mo-rt-deltas { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
        .delta-column { display: flex; flex-direction: column; gap: 10px; }
        .delta-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
        .delta-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 10px; }
        .delta-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; }
        .delta-value { font-size: 13px; font-weight: 700; }
        .delta-sub { font-size: 11px; opacity: 0.8; }

        .bbo-card { display: grid; grid-template-columns: 1fr 1px 1fr; gap: 0; }
        .bbo-section { padding: 6px 8px; }
        .bbo-head { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7; }
        .bbo-main { font-size: 14px; font-weight: 700; }
        .bbo-sub { font-size: 11px; opacity: 0.8; }
        .bbo-divider { width: 1px; background: rgba(255,255,255,0.1); }

        .mo-rt-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 8px; }
        .meta { background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); padding: 8px 10px; }
        .meta-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-bottom: 4px; }
        .meta-value { font-size: 13px; font-weight: 700; }

        .mo-rt-placeholder { font-size: 12px; opacity: 0.75; padding: 8px 10px; }

        .mo-rt-right-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .mo-rt-stats-title, .intraday-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-bottom: 6px; }
        .mo-rt-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
        .stat { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 10px; }
        .stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; }
        .stat-value { font-size: 13px; font-weight: 700; }

        .intraday-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
        .intraday-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 10px; }
        .intraday-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; }
        .intraday-value { font-size: 13px; font-weight: 700; }
        .intraday-empty { font-size: 12px; opacity: 0.75; }

        /* TOTAL session summary */
        .total-session-card { display: flex; flex-direction: column; gap: 12px; }
        .session-summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
        @media (min-width: 1200px) {
          .session-summary-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
        }
        .session-summary-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 14px; }
        .summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-bottom: 6px; }
        .summary-value { font-size: 18px; font-weight: 700; }
        .summary-sub { font-size: 13px; opacity: 0.85; margin-top: 4px; }

        /* Compact session stats under TOTAL */
        .mo-rt-session-stats { margin-top: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.35); padding: 8px 10px; font-size: 11px; }
        .session-stats-header,
        .session-stats-row { display: grid; grid-template-columns: minmax(0, 1.25fr) repeat(3, minmax(0, 0.95fr)); gap: 10px; align-items: center; }
        .session-stats-header { text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px; opacity: 0.7; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; margin-bottom: 4px; }
        .session-stats-header span,
        .session-stats-row span { text-align: center; }
        .session-stats-header span:first-child,
        .session-stats-row span:first-child { text-align: left; }
        .session-stats-row + .session-stats-row { margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,0.08); }
        .session-stats-row span:nth-child(2),
        .session-stats-row span:nth-child(4) { font-variant-numeric: tabular-nums; }
        .triangle-cell { display:flex; align-items:center; justify-content:center; }
        .triangle-percent { font-size: 11px; font-weight: 600; }
        .triangle-up { width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 10px solid #5cc569; }
        .triangle-down { width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 10px solid #f26d6d; }
        .triangle-neutral { width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 10px solid #bbb; border-bottom: 10px solid #bbb; }

        @media (max-width: 900px) {
          .mo-rt-right { min-width: 0; }
          .mo-rt-right-columns { grid-template-columns: 1fr; }
        }
      `}</style>
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
          const totalWeightedAverage = formatNum(snap?.weighted_average, 3) ?? (isZero(snap?.weighted_average) ? 0 : "—");
          const totalInstrumentCount = snap?.instrument_count ?? 11;
          const sessionDateLabel = getSessionDateKey(snap) ?? "—";
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
          const lastPriceDisplay = formatNum(snap?.last_price) ?? (isZero(snap?.last_price) ? 0 : "—");
          const openPrimary = openDeltaMetric.primary ?? "—";
          const totalSummaryCards: Array<{
            key: string;
            label: string;
            value: string | number;
            subtitle?: string | number;
          }> = [
            { key: "bid", label: "Bid", value: `${bidPriceDisplay}`, subtitle: `Size ${bidSizeDisplay}` },
            { key: "basket", label: "Futures in Basket", value: totalInstrumentCount, subtitle: undefined },
            { key: "total-avg", label: "Total Weighted Avg", value: totalWeightedAverage, subtitle: undefined },
            { key: "local-date", label: "Local Date", value: sessionDateLabel, subtitle: undefined },
          ];
          const totalSessionStatsRows = [
            {
              key: "market-open",
              label: "Market Open",
              value: formatNumOrDash(snap?.open_price_24h),
              triangleValue: snap?.market_open,
              percent: buildPercentCell(snap?.market_open),
            },
            {
              key: "market-high",
              label: "Market High",
              value: formatNumOrDash(snap?.high_24h),
              triangleValue: snap?.market_high_pct_open,
              percent: buildPercentCell(snap?.market_high_pct_open),
            },
            {
              key: "market-low",
              label: "Market Low",
              value: formatNumOrDash(snap?.low_24h),
              triangleValue: snap?.market_low_pct_open,
              percent: buildPercentCell(snap?.market_low_pct_open),
            },
            {
              key: "market-close",
              label: "Market Close",
              value: formatNumOrDash(snap?.prev_close_24h),
              triangleValue: snap?.market_close_vs_open_pct,
              percent: buildPercentCell(snap?.market_close_vs_open_pct),
            },
            {
              key: "range",
              label: "Range",
              value: formatNumOrDash(snap?.market_range),
              triangleValue: snap?.market_range_pct,
              percent: buildPercentCell(snap?.market_range_pct),
            },
            {
              key: "session-volume",
              label: "Session Volume",
              value: formatNumOrDash(snap?.volume, 0),
              triangleValue: null,
              percent: buildPercentCell(undefined, "--"),
            },
          ];
          const prevCloseNum = parseNumericValue(snap?.prev_close_24h);
          const low52Num = parseNumericValue(snap?.low_52w);
          const high52Num = parseNumericValue(snap?.high_52w);
          const low52DeltaPercent = (prevCloseNum !== null && low52Num !== null && prevCloseNum !== 0)
            ? ((prevCloseNum - low52Num) / prevCloseNum) * 100
            : null;
          const high52DeltaPercent = (prevCloseNum !== null && high52Num !== null && prevCloseNum !== 0)
            ? ((high52Num - prevCloseNum) / prevCloseNum) * 100
            : null;
          const sessionRangeValue = snap?.range_diff_24h
            ? `${formatNum(snap?.range_diff_24h)} (${formatNum(snap?.range_pct_24h) ?? "—"})`
            : "—";
          const detailedSessionStatsRows = [
            {
              key: "close",
              label: "Close",
              value: formatNumOrDash(snap?.prev_close_24h),
              triangleValue: snap?.market_close_vs_open_pct,
              percent: buildPercentCell(snap?.market_close_vs_open_pct),
            },
            {
              key: "open",
              label: "Open",
              value: formatNumOrDash(snap?.open_price_24h),
              triangleValue: snap?.market_open,
              percent: buildPercentCell(snap?.market_open),
            },
            {
              key: "low24",
              label: "24h Low",
              value: formatNumOrDash(snap?.low_24h),
              triangleValue: snap?.market_low_pct_open,
              percent: buildPercentCell(snap?.market_low_pct_open),
            },
            {
              key: "high24",
              label: "24h High",
              value: formatNumOrDash(snap?.high_24h),
              triangleValue: snap?.market_high_pct_open,
              percent: buildPercentCell(snap?.market_high_pct_open),
            },
            {
              key: "range24",
              label: "24h Range",
              value: sessionRangeValue,
              triangleValue: snap?.market_range_pct,
              percent: buildPercentCell(snap?.market_range_pct),
            },
            {
              key: "low52",
              label: "52w Low",
              value: formatNumOrDash(snap?.low_52w),
              triangleValue: low52DeltaPercent,
              percent: buildPercentCell(low52DeltaPercent),
            },
            {
              key: "high52",
              label: "52w High",
              value: formatNumOrDash(snap?.high_52w),
              triangleValue: high52DeltaPercent,
              percent: buildPercentCell(high52DeltaPercent),
            },
          ];

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
                  <div className="total-session-card">
                    <div className="mo-rt-top total">
                      <div className="mo-rt-last">
                        <div className="val">{lastPriceDisplay}</div>
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

                    <div className="session-summary-grid">
                      {totalSummaryCards.map(card => (
                        <div className="session-summary-card" key={card.key}>
                          <div className="summary-label">{card.label}</div>
                          <div className="summary-value">{card.value}</div>
                          {card.subtitle && <div className="summary-sub">{card.subtitle}</div>}
                        </div>
                      ))}
                    </div>

                    <div className="mo-rt-session-stats">
                      <div className="session-stats-header">
                        <span>Metric</span>
                        <span>Value</span>
                        <span>Δ</span>
                        <span>Δ%</span>
                      </div>
                      {totalSessionStatsRows.map(row => (
                        <div className="session-stats-row" key={row.key}>
                          <span>{row.label}</span>
                          <span>{row.value}</span>
                          <span className="triangle-cell">
                            <span className={getTriangleClass(row.triangleValue)} />
                          </span>
                          <span className={`triangle-percent ${row.percent.className}`}>{row.percent.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mo-rt-top">
                      <div className="mo-rt-last">
                        <div className="val">{lastPriceDisplay}</div>
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

                    {/* Four-column session stats under non-TOTAL */}
                    <div className="mo-rt-session-stats">
                      <div className="session-stats-header">
                        <span>Metric</span>
                        <span>Value</span>
                        <span>Δ</span>
                        <span>Δ%</span>
                      </div>
                      {detailedSessionStatsRows.map(row => (
                        <div className="session-stats-row" key={row.key}>
                          <span>{row.label}</span>
                          <span>{row.value}</span>
                          <span className="triangle-cell">
                            <span className={getTriangleClass(row.triangleValue)} />
                          </span>
                          <span className={`triangle-percent ${row.percent.className}`}>{row.percent.text}</span>
                        </div>
                      ))}
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
