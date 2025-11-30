// src/pages/FutureTrading/FutureRTD/RTDcards/shared.ts
import type { Theme } from "@mui/material/styles";
import type { MarketData } from "../types";

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
  const prevClose = toNumber(row.previous_close);
  const openPrice = toNumber(row.open_price);
  const low24 = toNumber(row.low_price);
  const high24 = toNumber(row.high_price);
  const low52 = toNumber((row.extended_data as any)?.low_52w);
  const high52 = toNumber((row.extended_data as any)?.high_52w);

  const closeDelta = toNumber((row as any).last_prev_diff);
  const closeDeltaPct = toNumber((row as any).last_prev_pct);

  const openDelta = toNumber((row as any).open_prev_diff);
  const openDeltaPct = toNumber((row as any).open_prev_pct);

  const lowDelta = toNumber((row as any).low_prev_diff);
  const lowDeltaPct = toNumber((row as any).low_prev_pct);
  const highDelta = toNumber((row as any).high_prev_diff);
  const highDeltaPct = toNumber((row as any).high_prev_pct);

  const above52 = toNumber((row as any).last_52w_above_low_diff);
  const above52Pct = toNumber((row as any).last_52w_above_low_pct);
  const below52 = toNumber((row as any).last_52w_below_high_diff);
  const below52Pct = toNumber((row as any).last_52w_below_high_pct);

  const rangeValue = toNumber((row as any).range_diff);
  const rangePct = toNumber((row as any).range_pct);

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
