import { motion } from "framer-motion";
import { Box, Chip, Paper, Typography } from "@mui/material";
import type { Theme } from "@mui/material/styles";

import type { TotalData } from "./types";
import { fmt } from "./utils/format";
import { signalChipColor, signalLabel } from "./utils/signals";

type TotalCardProps = {
  total: TotalData | null;
  theme: Theme;
};

export default function TotalCard({ total, theme }: TotalCardProps) {
  const count = (total as any)?.count ?? (total as any)?.instrument_count ?? 0;
  const weightedAvg = total?.avg_weighted ? fmt(total.avg_weighted, 3) : "—";
  const sumWeighted = total?.sum_weighted ? fmt(total.sum_weighted, 2) : "—";
  const signalWeight =
    typeof total?.signal_weight_sum === "number"
      ? fmt(total.signal_weight_sum, 2)
      : total?.signal_weight_sum
      ? fmt(total.signal_weight_sum, 2)
      : "—";
  const compositeSignal = total?.composite_signal;
  const updatedTime = total?.as_of ? new Date(total.as_of).toLocaleTimeString() : "—";

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Paper
        elevation={5}
        sx={{
          width: 500,
          height: "100%",
          overflow: "hidden",
          borderRadius: 2,
          background: `linear-gradient(135deg, ${theme.palette.warning.main}, ${theme.palette.warning.dark})`,
          border: `2px solid ${theme.palette.warning.light}`,
          color: theme.palette.warning.contrastText,
        }}
      >
        <Box
          sx={{
            px: 2,
            py: 1,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: theme.palette.warning.dark,
          }}
        >
          <Typography variant="body2" fontWeight="bold">
            TOTAL
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            {count} Futures
          </Typography>
        </Box>

        <Box p={2}>
          <Box
            display="grid"
            gridTemplateColumns="repeat(2, 1fr)"
            gap={1.5}
          >
            <Tile label="Weighted Avg" value={weightedAvg} />
            <Tile label="Sum Weighted" value={sumWeighted} />
            <Tile
              label="Composite Signal"
              value={
                compositeSignal ? (
                  <Chip
                    label={signalLabel(compositeSignal)}
                    color={signalChipColor(compositeSignal)}
                    size="small"
                    variant="filled"
                    sx={{ fontWeight: "bold", fontSize: "0.7rem" }}
                  />
                ) : (
                  "—"
                )
              }
            />
            <Tile label="Signal Weight" value={signalWeight} />
          </Box>

          <Box mt={2} display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)" }}>
              Updated {updatedTime}
            </Typography>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)" }}>
              Composite
            </Typography>
          </Box>
        </Box>
      </Paper>
    </motion.div>
  );
}

type TileProps = {
  label: string;
  value: React.ReactNode;
};

function Tile({ label, value }: TileProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        bgcolor: "rgba(255,255,255,0.1)",
        borderColor: "rgba(255,255,255,0.2)",
        textAlign: "center",
        color: "white",
        minHeight: 88,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", mb: 0.5 }}>
        {label}
      </Typography>
      {typeof value === "string" ? (
        <Typography variant="body2" fontWeight="bold">
          {value}
        </Typography>
      ) : (
        value
      )}
    </Paper>
  );
}
