// src/pages/Futures/Market/marketSessionUtils.ts
import type { MarketOpenSession } from "./marketSessionTypes.ts";

export const chipClass = (kind: "signal" | "status", value?: string) => {
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

export const formatNum = (n?: string | number | null, maxFrac = 2) => {
  if (n === null || n === undefined || n === "") return undefined;
  if (typeof n === "number") {
    return n.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
  }
  const s = String(n);
  const p = Number(s.replace(/,/g, ""));
  if (Number.isNaN(p)) return s;
  return p.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
};

export const parseNumericValue = (value?: string | number | null) => {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }
  const parsed = Number(String(value).replace(/,/g, ""));
  return Number.isNaN(parsed) ? null : parsed;
};

export const formatSignedValue = (
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

export const formatPercentValue = (
  value?: string | number | null,
  options?: { maxFrac?: number; showPlus?: boolean }
) => {
  const formatted = formatSignedValue(value, { maxFrac: options?.maxFrac ?? 2, showPlus: options?.showPlus ?? true });
  return formatted ? `${formatted}%` : undefined;
};

export const getDeltaClass = (value?: string | number | null) => {
  const parsed = parseNumericValue(value);
  if (parsed === null || parsed === 0) return "delta-neutral";
  return parsed > 0 ? "delta-positive" : "delta-negative";
};

export const getTriangleClass = (value?: string | number | null) => {
  const deltaClass = getDeltaClass(value);
  if (deltaClass === "delta-positive") return "triangle-up";
  if (deltaClass === "delta-negative") return "triangle-down";
  return "triangle-neutral";
};

export const buildPercentCell = (value?: string | number | null, fallback = "—") => {
  return {
    text: formatPercentValue(value) ?? fallback,
    className: getDeltaClass(value),
  };
};

export const isZero = (v: unknown) => v === 0 || v === "0";

export const formatNumOrDash = (value?: string | number | null, maxFrac = 2) => {
  const formatted = formatNum(value, maxFrac);
  if (formatted !== undefined) return formatted;
  return isZero(value) ? 0 : "—";
};

export const buildDateKey = (year?: number | null, month?: number | null, day?: number | null) => {
  if (!year || !month || !day) return undefined;
  const paddedMonth = String(month).padStart(2, "0");
  const paddedDay = String(day).padStart(2, "0");
  return `${year}-${paddedMonth}-${paddedDay}`;
};

export const getSessionDateKey = (session?: Pick<MarketOpenSession, "year" | "month" | "date"> | null) => {
  if (!session) return undefined;
  return buildDateKey(session.year, session.month, session.date);
};

export const normalizeCountry = (c?: string) => (c || "").trim().toLowerCase();

export const isToday = (iso?: string) => {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
};

export const formatIntradayValue = (value?: number | null, maxFrac = 2) => {
  if (value === null || value === undefined) return "—";
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return "—";
  return parsed.toLocaleString("en-US", { maximumFractionDigits: maxFrac });
};

// ---- API URL helpers ----

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const getBaseApiUrl = () => {
  const base = import.meta.env.VITE_API_BASE_URL;
  return base ? trimTrailingSlash(base) : undefined;
};

export const getApiUrl = () => {
  const explicit = import.meta.env.VITE_MARKET_OPENS_API_URL;
  if (explicit) return trimTrailingSlash(explicit);
  const base = getBaseApiUrl();
  if (base) return `${base}/market-opens/latest/`;
  return "http://127.0.0.1:8000/api/market-opens/latest/";
};

export const getLiveStatusApiUrl = () => {
  const explicit = import.meta.env.VITE_GLOBAL_MARKETS_LIVE_STATUS_API_URL;
  if (explicit) return trimTrailingSlash(explicit);
  const base = getBaseApiUrl();
  if (base) return `${base}/global-markets/markets/live_status/`;
  return "http://127.0.0.1:8000/api/global-markets/markets/live_status/";
};

export const getSessionApiUrl = () => {
  const explicit = import.meta.env.VITE_MARKET_SESSION_API_URL || import.meta.env.VITE_SESSION_API_URL;
  if (explicit) return trimTrailingSlash(explicit);
  const backendBase = import.meta.env.VITE_BACKEND_BASE_URL;
  if (backendBase) return `${trimTrailingSlash(backendBase)}/api/session`;
  const apiBase = getBaseApiUrl();
  if (apiBase) return `${apiBase}/session`;
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${trimTrailingSlash(window.location.origin)}/api/session`;
  }
  return "http://127.0.0.1:8000/api/session";
};

export const getIntradayHealthApiUrl = () => {
  const explicit = import.meta.env.VITE_INTRADAY_HEALTH_API_URL;
  if (explicit) return trimTrailingSlash(explicit);
  const backendBase = import.meta.env.VITE_BACKEND_BASE_URL;
  if (backendBase) return `${trimTrailingSlash(backendBase)}/api/intraday/health`;
  const apiBase = getBaseApiUrl();
  if (apiBase) return `${apiBase}/intraday/health`;
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${trimTrailingSlash(window.location.origin)}/api/intraday/health`;
  }
  return "http://127.0.0.1:8000/api/intraday/health";
};

// Map dashboard key to backend session market_code
export const marketKeyToCode = (key: string) => {
  switch (key) {
    case "Tokyo": return "Tokyo";
    case "Bombay": return "India";
    case "London": return "London";
    case "Pre_USA": return "Pre_USA";
    case "USA": return "USA";
    default: return key;
  }
};

