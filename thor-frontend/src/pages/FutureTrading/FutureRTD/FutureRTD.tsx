import "./FutureRTD.css";

import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, CircularProgress, Container, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { RefreshCw } from "lucide-react";

import L1Card from "./L1Card";
import TotalCard from "./TotalCard";
import { useFuturesQuotes } from "./hooks/useFuturesQuotes";
import type { FutureRTDProps, MarketData, RoutingPlanResponse } from "./types";

const FUTURES_11 = [
  "/YM",
  "/ES",
  "/NQ",
  "RTY",
  "CL",
  "SI",
  "HG",
  "GC",
  "VX",
  "DX",
  "ZB",
];

const POLL_STEPS = [2000, 1000, 5000];

const normalizeSymbol = (symbol: string) => symbol.replace(/^\//, "").toUpperCase();

function makePlaceholder(symbol: string, index: number): MarketData {
  return {
    instrument: {
      id: index + 1,
      symbol,
      name: symbol,
      exchange: "—",
      currency: "USD",
      display_precision: 2,
      tick_value: null,
      margin_requirement: null,
      is_active: true,
      sort_order: index,
    },
    price: null,
    bid: null,
    ask: null,
    last_size: null,
    bid_size: null,
    ask_size: null,
    open_price: null,
    high_price: null,
    low_price: null,
    close_price: null,
    previous_close: null,
    change: null,
    change_percent: null,
    vwap: null,
    volume: null,
    market_status: "CLOSED",
    data_source: "placeholder",
    is_real_time: false,
    delay_minutes: 0,
    extended_data: {},
    timestamp: new Date().toISOString(),
  } as MarketData;
}

export default function FutureRTD({ onToggleMarketOpen, showMarketOpen }: FutureRTDProps = {}) {
  const theme = useTheme();
  const [pollMs, setPollMs] = useState(2000);
  const { rows, total, loading, error } = useFuturesQuotes(pollMs);
  // TEMP DEBUG: toggle to render backend rows directly (bypass mapping)
  const [debugDirectRows, setDebugDirectRows] = useState(false);

  const [routingPlan, setRoutingPlan] = useState<RoutingPlanResponse | null>(null);
  const [routingLoading, setRoutingLoading] = useState(true);
  const [routingError, setRoutingError] = useState<string | null>(null);

  const [quantities, setQuantities] = useState<Record<string, number>>({});

  useEffect(() => {
    setRoutingLoading(false);
    setRoutingError(null);
    setRoutingPlan({
      consumer: { code: "futures_trading", display_name: "Futures Trading" },
      primary_feed: {
        code: "TOS_RTD",
        display_name: "TOS Excel RTD",
        connection_type: "direct",
        provider_key: "tos",
        priority: 1,
        is_primary: true,
      },
      feeds: [],
    });
  }, []);

  const orderedRows = useMemo(() => {
    // Build a map from base symbol letters (e.g., YM, ES) to the first row
    const byBase = new Map<string, MarketData>();

    rows.forEach((row) => {
      const norm = normalizeSymbol(row.instrument.symbol); // e.g., "/YMZ25" -> "YMZ25"
      const base = norm.match(/^[A-Z]+/)?.[0] ?? norm; // "YM"
      if (!byBase.has(base)) {
        byBase.set(base, row);
      }
    });

    return FUTURES_11.map((sym, idx) => {
      const norm = normalizeSymbol(sym); // "/YM" -> "YM"
      const base = norm.match(/^[A-Z]+/)?.[0] ?? norm;
      return byBase.get(base) ?? makePlaceholder(sym, idx);
    });
  }, [rows]);

  const rowsToRender = debugDirectRows ? rows : orderedRows;

  const handlePollCycle = () => {
    const currentIndex = POLL_STEPS.findIndex((step) => step === pollMs);
    const nextIndex = (currentIndex + 1) % POLL_STEPS.length;
    setPollMs(POLL_STEPS[nextIndex]);
  };

  const getQty = (symbol: string) => quantities[symbol] ?? 1;
  const setQty = (symbol: string, qty: number) => {
    setQuantities((prev) => ({ ...prev, [symbol]: Math.max(1, qty) }));
  };

  return (
    <Container maxWidth={false} sx={{ py: 3 }}>
      {(routingLoading || routingError) && (
        <Box mb={2}>
          {routingLoading ? (
            <Box display="flex" alignItems="center" gap={1}>
              <CircularProgress size={20} />
              <Typography variant="body2">Loading feed routing…</Typography>
            </Box>
          ) : routingError ? (
            <Alert severity="warning">{routingError}</Alert>
          ) : null}
        </Box>
      )}

      {routingPlan && (
        <Box mb={2} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Feed: {routingPlan.primary_feed?.display_name ?? "Not configured"}
          </Typography>
          {onToggleMarketOpen && (
            <Button
              variant="text"
              size="small"
              onClick={onToggleMarketOpen}
              sx={{
                color: "white",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 0.1)",
                },
              }}
            >
              {showMarketOpen ? "📊 Hide" : "📊 Show"} Market Open Sessions
            </Button>
          )}
        </Box>
      )}

      {loading && (
        <Box mb={2} display="flex" alignItems="center" gap={1}>
          <CircularProgress size={20} />
          <Typography variant="body2">Refreshing quotes…</Typography>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box display="flex" justifyContent="flex-end" alignItems="center" mb={3}>
        <Button
          variant="outlined"
          onClick={handlePollCycle}
          startIcon={<RefreshCw size={16} />}
          title="Toggle polling interval"
          sx={{
            borderColor: "white",
            color: "white",
            "&:hover": {
              borderColor: "rgba(255, 255, 255, 0.8)",
              backgroundColor: "rgba(255, 255, 255, 0.1)",
            },
          }}
        >
          {pollMs / 1000}s
        </Button>
        <Button
          variant="outlined"
          onClick={() => setDebugDirectRows((v) => !v)}
          title="Debug: render backend rows directly"
          sx={{
            ml: 1,
            borderColor: debugDirectRows ? theme.palette.warning.light : "white",
            color: debugDirectRows ? theme.palette.warning.light : "white",
            "&:hover": {
              borderColor: "rgba(255, 255, 255, 0.8)",
              backgroundColor: "rgba(255, 255, 255, 0.1)",
            },
          }}
        >
          {debugDirectRows ? "Debug: Direct Rows" : "Debug: Mapped Rows"}
        </Button>
      </Box>

      <Box sx={{ overflowX: "auto", pb: 2 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(6, 500px)",
            gridTemplateRows: "repeat(2, auto)",
            gap: 2,
            width: "fit-content",
            minWidth: "100%",
          }}
        >
          <Box>
            <TotalCard total={total} theme={theme} />
          </Box>

          {rowsToRender.slice(0, 11).map((row) => (
            <Box key={row.instrument.symbol}>
              <L1Card
                row={row}
                theme={theme}
                quantity={getQty(row.instrument.symbol)}
                onQuantityChange={(nextQty) => setQty(row.instrument.symbol, nextQty)}
              />
            </Box>
          ))}
        </Box>
      </Box>
    </Container>
  );
}

