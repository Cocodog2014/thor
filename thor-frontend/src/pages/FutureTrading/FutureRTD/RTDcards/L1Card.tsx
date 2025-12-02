// src/pages/FutureTrading/FutureRTD/RTDcards/L1Card.tsx
import { motion } from "framer-motion";
import { Box, Paper, Typography } from "@mui/material";
import type { Theme } from "@mui/material/styles";

import type { MarketData } from "../types";
import { fmt } from "../utils/format";
import { L1Header } from "./L1Header";
import { L1BidAsk } from "./L1BidAsk";
import { L1QtyPanel } from "./L1QtyPanel";
import { L1MetricsGrid } from "./L1MetricsGrid";
import { buildMetricRows, deltaColor, toNumber } from "./shared";

type L1CardProps = {
  row: MarketData;
  theme: Theme;
  quantity: number;
  onQuantityChange: (nextQuantity: number) => void;
};

export default function L1Card({ row, theme, quantity, onQuantityChange }: L1CardProps) {
  const precision = row.instrument.display_precision ?? 2;

  // Backend-provided metrics
  type InlineMetrics = {
    last_prev_diff?: number | string | null;
    last_prev_pct?: number | string | null;
    spread?: number | string | null;
  };
  const r = row as MarketData & InlineMetrics;
  const netChange = toNumber(r.last_prev_diff);
  const changePct = toNumber(r.last_prev_pct);
  const spread = toNumber(r.spread);

  const tickValue = toNumber(row.instrument.tick_value);
  const marginRequirement = toNumber(row.instrument.margin_requirement);
  const volumeDisplay = row.volume == null ? "—" : fmt(row.volume, 0);

  const metricRows = buildMetricRows(row);

  const handleIncrement = () => onQuantityChange(quantity + 1);
  const handleDecrement = () => onQuantityChange(Math.max(1, quantity - 1));

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Paper
        className="futures-card l1card-root"
        elevation={3}
        sx={{
          background: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <L1Header row={row} theme={theme} />

        <Box
          p={1.5}
          className="l1-body"
          sx={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden" }}
        >
          <Box display="flex" gap={2}>
            <Box flex={1}>
              {/* Last + Change */}
              <Box display="flex" justifyContent="space-between" gap={2}>
                <Box>
                  <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
                    {fmt(row.price, precision)}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 0.5, display: "block" }}
                  >
                    Last
                  </Typography>
                </Box>
                <Box textAlign="right">
                  <Box className="l1card-price-row">
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      sx={{
                        color: deltaColor(netChange, theme),
                        lineHeight: 1,
                      }}
                    >
                      {netChange === null ? "—" : fmt(netChange, precision)}
                    </Typography>
                    <Typography
                      variant="subtitle2"
                      fontWeight="bold"
                      sx={{
                        color: deltaColor(changePct, theme),
                        lineHeight: 1,
                        mt: "2px",
                      }}
                    >
                      {changePct === null ? "—" : `${fmt(changePct, 2)}%`}
                    </Typography>
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 0.5, display: "block" }}
                  >
                    Change
                  </Typography>
                </Box>
              </Box>

              {/* Bid / Ask */}
              <L1BidAsk
                bid={toNumber(row.bid)}
                ask={toNumber(row.ask)}
                bidSize={row.bid_size}
                askSize={row.ask_size}
                precision={precision}
                fmt={fmt}
                theme={theme}
              />

              {/* Qty Panel */}
              <L1QtyPanel
                quantity={quantity}
                onIncrement={handleIncrement}
                onDecrement={handleDecrement}
                tickValue={tickValue}
                marginRequirement={marginRequirement}
                fmt={fmt}
              />

              {/* Mini stats: Volume / VWAP */}
              <Box className="l1card-mini-grid">
                <Paper variant="outlined" sx={{ p: 1, textAlign: "center", minHeight: 70 }}>
                  <Typography variant="caption" color="text.secondary">
                    Volume
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {volumeDisplay}
                  </Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 0.75, textAlign: "center", minHeight: 70 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontSize: "0.7rem" }}
                  >
                    VWAP
                  </Typography>
                  <Typography variant="body2" fontWeight="medium" sx={{ my: 0.25 }}>
                    {fmt(row.vwap, precision)}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.disabled"
                    sx={{ fontSize: "0.65rem" }}
                  >
                    Spread {fmt(spread, precision)}
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Box>

          {/* Metrics grid */}
          <L1MetricsGrid rows={metricRows} precision={precision} theme={theme} />
        </Box>
      </Paper>
    </motion.div>
  );
}
