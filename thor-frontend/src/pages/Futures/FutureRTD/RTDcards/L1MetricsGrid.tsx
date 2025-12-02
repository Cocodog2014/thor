// src/pages/Futures/FutureRTD/RTDcards/L1MetricsGrid.tsx
import { Box, Typography } from "@mui/material";
import type { Theme } from "@mui/material/styles";

import { fmt } from "../utils/format";
import type { MetricRow } from "./shared";
import { GRID_TEMPLATE, deltaColor } from "./shared";

type L1MetricsGridProps = {
  rows: MetricRow[];
  precision: number;
  theme: Theme;
};

export function L1MetricsGrid({ rows, precision, theme }: L1MetricsGridProps) {
  return (
    <Box className="data-grid l1card-data-grid">
      <Box className="stat-header l1card-stat-header">
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

      {rows.map((metric) => {
        const valueDisplay = metric.value == null ? "—" : fmt(metric.value, precision);
        const deltaDisplay = metric.delta == null ? "—" : fmt(metric.delta, precision);
        const deltaPctDisplay =
          metric.deltaPct == null ? "—" : `${fmt(metric.deltaPct, 2)}%`;

        return (
          <Box key={metric.label} className="stat-row l1card-stat-row">
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
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: deltaColor(metric.delta, theme),
                  }}
                >
                  {deltaDisplay}
                </Typography>
              </Box>
              <Box textAlign="right">
                <Typography
                  variant="body2"
                  fontWeight="medium"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: deltaColor(metric.deltaPct, theme),
                  }}
                >
                  {deltaPctDisplay}
                </Typography>
              </Box>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
