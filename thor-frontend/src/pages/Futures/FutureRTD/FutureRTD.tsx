import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, CircularProgress, Container, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

import { L1Card } from "./RTDcards";
import TotalCard from "./TotalCard";
import { useFuturesQuotes } from "./hooks";
import type { FutureRTDProps, MarketData, RoutingPlanResponse } from "./types";

// ----------------------------- Config ----------------------------

const FUTURES_11 = [
  "/YM",
  "/ES",
  "/NQ",
  "RTY", // equity index futures
  "CL",
  "SI",
  "HG",
  "GC", // energy & metals
  "VX",
  "DX",
  "ZB", // vol, dollar, 30Y
];

const normalizeSymbol = (symbol: string) => symbol.replace(/^\//, "").toUpperCase();

// Helper to create an empty placeholder row for missing symbols
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

// -------------------------- Main Component -----------------------

export default function FutureRTD({ onToggleMarketOpen, showMarketOpen }: FutureRTDProps = {}) {
  const theme = useTheme();

  // ✅ Single source of truth for quotes
  const { rows, total, loading, error, hasLoadedOnce } = useFuturesQuotes();

  const [routingPlan, setRoutingPlan] = useState<RoutingPlanResponse | null>(null);
  const [routingError, setRoutingError] = useState<string | null>(null);
  const [routingLoading, setRoutingLoading] = useState(true);

  const [quantities, setQuantities] = useState<Record<string, number>>({});

  const getQty = (symbol: string) => quantities[symbol] ?? 1;
  const setQty = (symbol: string, qty: number) => {
    setQuantities((prev) => ({ ...prev, [symbol]: Math.max(1, qty) }));
  };

  // ---------------- Routing setup (same behavior as before) -------

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

  // ---------------- Map to fixed 11 cards ------------------------

  const effective = rows;

  const ordered: MarketData[] = useMemo(() => {
    const map = new Map(effective.map((r) => [normalizeSymbol(r.instrument.symbol), r]));
    return FUTURES_11.map((sym: string, idx: number) => {
      const normalized = normalizeSymbol(sym);
      const found = map.get(normalized);
      if (!found) {
        console.warn("[FutureRTD] No data for symbol", sym, "-> using placeholder");
      }
      return found ?? makePlaceholder(sym, idx);
    });
  }, [effective]);

  const displayRows: MarketData[] = useMemo(() => ordered, [ordered]);

  // ---------------------------- Render ---------------------------

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
          <Box display="flex" alignItems="center" gap={1}>
            {hasLoadedOnce && loading && (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={12} thickness={5} />
                <Typography variant="caption" color="text.secondary">
                  Refreshing…
                </Typography>
              </Box>
            )}
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
        </Box>
      )}

      {loading && !hasLoadedOnce && (
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

      <Box sx={{ overflowX: "auto", pb: 2 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gridAutoRows: "auto",
            gap: 1.5,
            width: "100%",
          }}
        >
          {/* Row 1, Col 1: Total card */}
          <Box>
            <TotalCard total={total} theme={theme} />
          </Box>

          {/* Remaining rows auto-fill in FUTURES_11 order */}
          {displayRows.slice(0, 11).map((row) => (
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

