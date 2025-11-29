import { motion } from "framer-motion";
import {
  Box,
  Button,
  Chip,
  Paper,
  Typography,
} from "@mui/material";
import type { Theme } from "@mui/material/styles";

import type { MarketData } from "./types";
import { fmt } from "./utils/format";
import { signalChipColor, signalLabel } from "./utils/signals";

type L1CardProps = {
  row: MarketData;
  theme: Theme;
  quantity: number;
  onQuantityChange: (nextQuantity: number) => void;
};

const GRID_TEMPLATE = "1.5fr 1fr 1fr 1fr";

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const deltaColor = (value: number | null, theme: Theme) => {
  if (value === null) return theme.palette.text.secondary;
  if (value > 0) return theme.palette.success.main;
  if (value < 0) return theme.palette.error.main;
  return theme.palette.text.secondary;
};

export default function L1Card({ row, theme, quantity, onQuantityChange }: L1CardProps) {
  const precision = row.instrument.display_precision ?? 2;

  // Direct backend-provided metrics (no frontend recomputation)
  const prevClose = toNumber(row.previous_close);
  const openPrice = toNumber(row.open_price);
  const bid = toNumber(row.bid);
  const ask = toNumber(row.ask);
  const low24 = toNumber(row.low_price);
  const high24 = toNumber(row.high_price);
  const low52 = toNumber((row.extended_data as any)?.low_52w);
  const high52 = toNumber((row.extended_data as any)?.high_52w);

  const netChange = toNumber((row as any).last_prev_diff);
  const changePct = toNumber((row as any).last_prev_pct);
  const spread = toNumber((row as any).spread) ?? (bid !== null && ask !== null ? ask - bid : null);
  const signalWeight = (row.extended_data as any)?.signal_weight ?? null;
  const statValue = (row.extended_data as any)?.stat_value ?? null;
  const closeDelta = netChange;
  const closeDeltaPct = changePct;

  const openDelta = toNumber((row as any).open_prev_diff);
  const openDeltaPct = toNumber((row as any).open_prev_pct);

  const lowDelta = toNumber((row as any).low_prev_diff); // low - prevClose
  const lowDeltaPct = toNumber((row as any).low_prev_pct);
  const highDelta = toNumber((row as any).high_prev_diff); // high - prevClose
  const highDeltaPct = toNumber((row as any).high_prev_pct);

  const above52 = toNumber((row as any).last_52w_above_low_diff);
  const above52Pct = toNumber((row as any).last_52w_above_low_pct);
  const below52 = toNumber((row as any).last_52w_below_high_diff);
  const below52Pct = toNumber((row as any).last_52w_below_high_pct);

  const rangeValue = toNumber((row as any).range_diff) ?? (low24 !== null && high24 !== null ? high24 - low24 : null);

  const tickValue = toNumber(row.instrument.tick_value);
  const marginRequirement = toNumber(row.instrument.margin_requirement);
  const volumeDisplay = row.volume == null ? "—" : fmt(row.volume, 0);

  const handleIncrement = () => onQuantityChange(quantity + 1);
  const handleDecrement = () => onQuantityChange(Math.max(1, quantity - 1));

  const metricRows = [
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
      value: rangeValue,
      delta: null,
      deltaPct: toNumber((row as any).range_pct),
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

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Paper
        className="futures-card"
        elevation={3}
        sx={{
          width: 500,
          minHeight: 420,
          display: "flex",
          flexDirection: "column",
          borderRadius: 2,
          background: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box
          sx={{
            px: 2,
            py: 1,
            background: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="body2" fontWeight="bold">
            {row.instrument.symbol}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={signalLabel(row.extended_data?.signal as any)}
              color={signalChipColor(row.extended_data?.signal as any)}
              size="small"
              variant="filled"
              sx={{ fontSize: "0.65rem", fontWeight: "bold" }}
            />
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{
                color: "white",
                bgcolor: "rgba(255,255,255,0.2)",
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: "0.75rem",
              }}
            >
              Wgt: {signalWeight ?? "0"}
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{
                color: "white",
                bgcolor: "rgba(255,255,255,0.2)",
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: "0.75rem",
              }}
            >
              {statValue ? fmt(statValue, 3) : "—"}
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{ color: deltaColor(changePct, theme) }}
            >
              {changePct === null ? "—" : `${fmt(changePct, 2)}%`}
            </Typography>
          </Box>
        </Box>

        <Box
          p={2}
          className="l1-body"
          sx={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}
        >
          <Box display="flex" gap={2}>
            <Box flex={1}>
              <Box display="flex" justifyContent="space-between" gap={2}>
                <Box>
                  <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
                    {fmt(row.price, precision)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                    Last
                  </Typography>
                </Box>
                <Box textAlign="right">
                  <Box display="flex" justifyContent="flex-end" gap={1}>
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      sx={{ color: deltaColor(netChange, theme), lineHeight: 1 }}
                    >
                      {netChange === null ? "—" : fmt(netChange, precision)}
                    </Typography>
                    <Typography
                      variant="subtitle2"
                      fontWeight="bold"
                      sx={{ color: deltaColor(changePct, theme), lineHeight: 1, mt: "2px" }}
                    >
                      {changePct === null ? "—" : `${fmt(changePct, 2)}%`}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                    Change
                  </Typography>
                </Box>
              </Box>

              <Box
                sx={{
                  mt: 0.75,
                  display: "grid",
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: 1,
                }}
              >
                <Box
                  component="button"
                  sx={{
                    gridColumn: "1",
                    px: 1,
                    py: 1.2,
                    textAlign: "center",
                    background: theme.palette.success.dark,
                    border: "none",
                    borderRadius: 1,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    "&:hover": {
                      background: theme.palette.success.main,
                      transform: "scale(1.02)",
                    },
                  }}
                >
                  <Typography variant="caption" fontWeight="bold" sx={{ color: "white", mb: 0.5 }}>
                    BID
                  </Typography>
                  <Typography variant="h6" fontWeight="bold" sx={{ color: "white", lineHeight: 1 }}>
                    {fmt(row.bid, precision)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", mt: 0.35 }}>
                    Size {row.bid_size ?? "—"}
                  </Typography>
                </Box>

                <Box
                  component="button"
                  sx={{
                    gridColumn: "2",
                    px: 1,
                    py: 1.2,
                    textAlign: "center",
                    background: theme.palette.error.dark,
                    border: "none",
                    borderRadius: 1,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    "&:hover": {
                      background: theme.palette.error.main,
                      transform: "scale(1.02)",
                    },
                  }}
                >
                  <Typography variant="caption" fontWeight="bold" sx={{ color: "white", mb: 0.5 }}>
                    ASK
                  </Typography>
                  <Typography variant="h6" fontWeight="bold" sx={{ color: "white", lineHeight: 1 }}>
                    {fmt(row.ask, precision)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", mt: 0.35 }}>
                    Size {row.ask_size ?? "—"}
                  </Typography>
                </Box>
              </Box>

              <Paper
                variant="outlined"
                sx={{
                  mt: 1,
                  p: 1.5,
                  bgcolor: "rgba(255, 255, 255, 0.02)",
                  borderColor: "rgba(255, 255, 255, 0.1)",
                }}
              >
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                  <Typography variant="caption" fontWeight="medium" color="text.secondary">
                    Qty:
                  </Typography>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <Button size="small" variant="outlined" onClick={handleDecrement} sx={{ minWidth: 30, p: 0.5 }}>
                      -
                    </Button>
                    <Box
                      sx={{
                        px: 2,
                        py: 0.5,
                        bgcolor: "rgba(255,255,255,0.05)",
                        borderRadius: 1,
                        minWidth: 40,
                        textAlign: "center",
                      }}
                    >
                      <Typography variant="body2" fontWeight="bold">
                        {quantity}
                      </Typography>
                    </Box>
                    <Button size="small" variant="outlined" onClick={handleIncrement} sx={{ minWidth: 30, p: 0.5 }}>
                      +
                    </Button>
                  </Box>
                </Box>

                <Box>
                  <Box display="flex" justifyContent="space-between" mb={0.5}>
                    <Typography variant="caption" color="text.secondary">
                      Qty × Tick 1 =
                    </Typography>
                    <Typography variant="caption" fontWeight="bold" color="primary.main">
                      {tickValue === null
                        ? "—"
                        : `$${fmt(tickValue * quantity, 2)}`}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="caption" color="text.secondary">
                      Qty × Margin Req =
                    </Typography>
                    <Typography variant="caption" fontWeight="bold" color="warning.main">
                      {marginRequirement === null
                        ? "—"
                        : `$${fmt(marginRequirement * quantity, 2)}`}
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              <Box
                sx={{
                  mt: 1,
                  display: "grid",
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: 1,
                }}
              >
                <Paper variant="outlined" sx={{ p: 1, textAlign: "center", minHeight: 70 }}>
                  <Typography variant="caption" color="text.secondary">
                    Volume
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {volumeDisplay}
                  </Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 0.75, textAlign: "center", minHeight: 70 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem" }}>
                    VWAP
                  </Typography>
                  <Typography variant="body2" fontWeight="medium" sx={{ my: 0.25 }}>
                    {fmt(row.vwap, precision)}
                  </Typography>
                  <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem" }}>
                    Spread {fmt(spread, precision)}
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Box>

          <Box mt={2} className="data-grid">
            <Box className="stat-header" mb={0.5} pb={0.5}>
              <Box display="grid" gridTemplateColumns={GRID_TEMPLATE} columnGap={1}>
                <Typography variant="caption" fontWeight="bold" color="text.secondary">
                  Metric
                </Typography>
                <Typography
                  variant="caption"
                  fontWeight="bold"
                  color="text.secondary"
                  textAlign="right"
                >
                  Value
                </Typography>
                <Typography
                  variant="caption"
                  fontWeight="bold"
                  color="text.secondary"
                  textAlign="right"
                >
                  Δ
                </Typography>
                <Typography
                  variant="caption"
                  fontWeight="bold"
                  color="text.secondary"
                  textAlign="right"
                >
                  Δ%
                </Typography>
              </Box>
            </Box>

            {metricRows.map((metric) => {
              const valueDisplay = metric.value == null ? "—" : fmt(metric.value, precision);
              const deltaDisplay = metric.delta == null ? "—" : fmt(metric.delta, precision);
              const deltaPctDisplay = metric.deltaPct == null ? "—" : `${fmt(metric.deltaPct, 2)}%`;

              return (
                <Box key={metric.label} className="stat-row" pt={0.5} mb={1}>
                  <Box display="grid" gridTemplateColumns={GRID_TEMPLATE} columnGap={1}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {metric.label}
                      </Typography>
                    </Box>
                    <Box textAlign="right">
                      <Typography
                        variant="body2"
                        fontWeight="medium"
                        sx={{ fontVariantNumeric: "tabular-nums" }}
                      >
                        {valueDisplay}
                      </Typography>
                    </Box>
                    <Box textAlign="right">
                      <Typography
                        variant="body2"
                        fontWeight="medium"
                        sx={{ fontVariantNumeric: "tabular-nums", color: deltaColor(metric.delta, theme) }}
                      >
                        {deltaDisplay}
                      </Typography>
                    </Box>
                    <Box textAlign="right">
                      <Typography
                        variant="body2"
                        fontWeight="medium"
                        sx={{ fontVariantNumeric: "tabular-nums", color: deltaColor(metric.deltaPct, theme) }}
                      >
                        {deltaPctDisplay}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Box>
      </Paper>
    </motion.div>
  );
}
