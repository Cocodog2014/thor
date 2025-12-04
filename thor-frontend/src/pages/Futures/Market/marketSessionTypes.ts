// src/pages/Futures/Market/marketSessionTypes.ts

// Single-table design: each row represents one future at one market open
export interface MarketOpenSession {
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

export type MarketLiveStatus = {
  next_event?: string;
  seconds_to_next_event?: number;
  current_state?: string;
  local_date_key?: string;
};

export type IntradaySnapshot = {
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  volume?: number | null;
  spread?: number | null;
};

// Control markets must use exact country strings from backend sessions.
// Backend currently stores: Japan, China, India, United Kingdom, Pre_USA, USA
export const CONTROL_MARKETS = [
  { key: "Tokyo",    label: "Tokyo",    country: "Japan" },
  { key: "Shanghai", label: "Shanghai", country: "China" },
  { key: "Bombay",   label: "Bombay",   country: "India" },
  { key: "London",   label: "London",   country: "United Kingdom" },
  { key: "Pre_USA",  label: "Pre-USA",  country: "Pre_USA" },
  { key: "USA",      label: "USA",      country: "USA" },
] as const;

// Futures universe: 10 futures + Dollar Index + TOTAL (composite)
export const FUTURE_OPTIONS = [
  { key: "YM",    label: "YM (Dow)" },
  { key: "ES",    label: "ES (S&P)" },
  { key: "NQ",    label: "NQ (Nasdaq)" },
  { key: "RTY",   label: "RTY (Russell)" },
  { key: "CL",    label: "CL (Crude)" },
  { key: "GC",    label: "GC (Gold)" },
  { key: "SI",    label: "SI (Silver)" },
  { key: "HG",    label: "HG (Copper)" },
  { key: "VX",    label: "VX (VIX)" },
  { key: "ZB",    label: "ZB (30Y)" },
  { key: "DX",    label: "DX (Dollar)" },
  { key: "TOTAL", label: "TOTAL (Composite)" },
] as const;

export {};
