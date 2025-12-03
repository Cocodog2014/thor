// src/pages/Futures/FutureRTD/RTDcards/L1QtyPanel.tsx
import { Box, Button, Paper, Typography } from "@mui/material";

type L1QtyPanelProps = {
  quantity: number;
  onIncrement: () => void;
  onDecrement: () => void;
  tickValue: number | null;
  marginRequirement: number | null;
  fmt: (value: number | null, decimals?: number) => string;
};

export function L1QtyPanel({
  quantity,
  onIncrement,
  onDecrement,
  tickValue,
  marginRequirement,
  fmt,
}: L1QtyPanelProps) {
  return (
    <Paper variant="outlined" className="l1card-qty-panel">
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="caption" fontWeight="medium" color="text.secondary">
          Qty:
        </Typography>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Button size="small" variant="outlined" onClick={onDecrement} sx={{ minWidth: 30, p: 0.5 }}>
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
          <Button size="small" variant="outlined" onClick={onIncrement} sx={{ minWidth: 30, p: 0.5 }}>
            +
          </Button>
        </Box>
      </Box>

      <Box>
        <Box display="flex" justifyContent="space-between" mb={0.5}>
          <Typography variant="caption" color="text.secondary">
            Tick Value =
          </Typography>
          <Typography variant="caption" fontWeight="bold" color="primary.main">
            {tickValue === null ? "—" : `$${fmt(tickValue, 2)}`}
          </Typography>
        </Box>
        <Box display="flex" justifyContent="space-between">
          <Typography variant="caption" color="text.secondary">
            Margin Req =
          </Typography>
          <Typography variant="caption" fontWeight="bold" color="warning.main">
            {marginRequirement === null ? "—" : `$${fmt(marginRequirement, 2)}`}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
