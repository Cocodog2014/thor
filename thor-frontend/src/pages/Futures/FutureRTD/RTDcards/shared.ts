// src/pages/Futures/FutureRTD/RTDcards/shared.ts
import type { Theme } from "@mui/material/styles";
import type { MarketData } from "../types";

// Optional backend-provided metric fields present on MarketData
type MetricsFields = {
  low_52w?: number | string | null;
  high_52w?: number | string | null;
  last_prev_diff?: number | string | null;
  last_prev_pct?: number | string | null;
  open_prev_diff?: number | string | null;
  open_prev_pct?: number | string | null;
  low_prev_diff?: number | string | null;
  low_prev_pct?: number | string | null;
  high_prev_diff?: number | string | null;
  high_prev_pct?: number | string | null;
  last_52w_above_low_diff?: number | string | null;
  last_52w_above_low_pct?: number | string | null;
  last_52w_below_high_diff?: number | string | null;
  last_52w_below_high_pct?: number | string | null;
  range_diff?: number | string | null;
  range_pct?: number | string | null;
};

export const GRID_TEMPLATE = "1.5fr 1fr 1fr 1fr";

export const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

export const deltaColor = (value: number | null, theme: Theme) => {
  if (value === null) return theme.palette.text.secondary;
  if (value > 0) return theme.palette.success.main;
  if (value < 0) return theme.palette.error.main;
  return theme.palette.text.secondary;
};

export type MetricRow = {
  label: string;
  value: number | null;
  delta: number | null;
  deltaPct: number | null;
};

export const buildMetricRows = (row: MarketData): MetricRow[] => {
  const r = row as MarketData & { extended_data?: MetricsFields } & MetricsFields;
  const prevClose = toNumber(row.previous_close);
  const openPrice = toNumber(row.open_price);
  const low24 = toNumber(row.low_price);
  const high24 = toNumber(row.high_price);
  const low52 = toNumber(r.extended_data?.low_52w);
  const high52 = toNumber(r.extended_data?.high_52w);
  const closeDelta = toNumber(r.last_prev_diff);
  const closeDeltaPct = toNumber(r.last_prev_pct);

  const openDelta = toNumber(r.open_prev_diff);
  const openDeltaPct = toNumber(r.open_prev_pct);

  const lowDelta = toNumber(r.low_prev_diff);
  const lowDeltaPct = toNumber(r.low_prev_pct);
  const highDelta = toNumber(r.high_prev_diff);
  const highDeltaPct = toNumber(r.high_prev_pct);

  const above52 = toNumber(r.last_52w_above_low_diff);
  const above52Pct = toNumber(r.last_52w_above_low_pct);
  const below52 = toNumber(r.last_52w_below_high_diff);
  const below52Pct = toNumber(r.last_52w_below_high_pct);

  const rangeValue = toNumber(r.range_diff);
  const rangePct = toNumber(r.range_pct);

  return [
    {
      label: "Close",
      value: prevClose,
      delta: closeDelta,
      deltaPct: closeDeltaPct,
    },
    {
      label: "Open",
      value: openPrice,
      delta: openDelta,
      deltaPct: openDeltaPct,
    },
    {
      label: "24h Low",
      value: low24,
      delta: lowDelta,
      deltaPct: lowDeltaPct,
    },
    {
      label: "24h High",
      value: high24,
      delta: highDelta,
      deltaPct: highDeltaPct,
    },
    {
      label: "24h Range",
      value: null,
      delta: rangeValue,
      deltaPct: rangePct,
    },
    {
      label: "52w Low",
      value: low52,
      delta: above52,
      deltaPct: above52Pct,
    },
    {
      label: "52w High",
      value: high52,
      delta: below52,
      deltaPct: below52Pct,
    },
  ];
};
