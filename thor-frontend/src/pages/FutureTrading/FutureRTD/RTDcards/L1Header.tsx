// src/pages/FutureTrading/FutureRTD/RTDcards/L1Header.tsx
import { Box, Chip, Typography } from "@mui/material";
import type { Theme } from "@mui/material/styles";

import type { MarketData } from "../types";
import { fmt } from "../utils/format";
import { signalChipColor, signalLabel } from "../utils/signals";
import { deltaColor, toNumber } from "./shared";

type L1HeaderProps = {
  row: MarketData;
  theme: Theme;
};

export function L1Header({ row, theme }: L1HeaderProps) {
  const changePct = toNumber((row as any).last_prev_pct);
  const signalWeight = (row.extended_data as any)?.signal_weight ?? null;
  const statValue = (row.extended_data as any)?.stat_value ?? null;

  return (
    <Box
      className="l1card-header"
      sx={{ background: theme.palette.primary.main, color: theme.palette.primary.contrastText }}
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
  );
}
