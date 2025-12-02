// src/pages/FutureTrading/FutureRTD/RTDcards/L1BidAsk.tsx
import { Box, Typography } from "@mui/material";
import type { Theme } from "@mui/material/styles";

type L1BidAskProps = {
  bid: number | null;
  ask: number | null;
  bidSize: number | null | undefined;
  askSize: number | null | undefined;
  precision: number;
  fmt: (value: number | null, decimals?: number) => string;
  theme: Theme;
};

export function L1BidAsk({
  bid,
  ask,
  bidSize,
  askSize,
  precision,
  fmt,
  theme,
}: L1BidAskProps) {
  return (
    <Box className="l1card-bidask-grid">
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
          {fmt(bid, precision)}
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", mt: 0.35 }}>
          Size {bidSize ?? "—"}
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
          {fmt(ask, precision)}
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", mt: 0.35 }}>
          Size {askSize ?? "—"}
        </Typography>
      </Box>
    </Box>
  );
}
