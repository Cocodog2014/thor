import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
// Sparkline removed
import { RefreshCw } from "lucide-react";
import {
  Box,
  Typography,
  Button,
  Paper,
  Chip,
  Container,
  Alert,
  CircularProgress,
} from "@mui/material";
import { useTheme, type Theme } from "@mui/material/styles";
import type { ChipProps } from "@mui/material";

/**
 * Level-1 12-Futures Dashboard (6x2) — with Signal box + VWAP box
 * ------------------------------------------------------------------
 * Shows 12 futures at once in a strict 6x2 grid with your Level-1 fields:
 * Open, Close(prev), Difference, 24h High/Low, Volume, Bid/Ask/Last + Sizes,
 * PLUS a dedicated Signal container and a dedicated VWAP (Weighted) box.
 *
 * Endpoints expected (Django):
 *   GET /api/quotes/latest  -> MarketData[] (latest row/instrument)
 *
 * If backend is unavailable, enable Mock Mode to simulate live ticks.
 * Your later script can populate `extended_data.signal` for each instrument
 * with one of: STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL.
 */

// ----------------------------- Config ----------------------------

const FUTURES_11 = [
  "/YM", "/ES", "/NQ", "RTY", // equity index futures
  "CL", "SI", "HG", "GC",       // energy & metals
  "VX", "DX", "ZB"              // vol, dollar, 30Y (removed ZN)
];

// ----------------------------- Types -----------------------------

type Instrument = {
  id: number;
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  display_precision: number;
  tick_value: string | null;
  margin_requirement: string | null;
  is_active: boolean;
  sort_order: number;
};

type MarketData = {
  instrument: Instrument;
  price: string; // last
  bid: string | null;
  ask: string | null;
  last_size: number | null;
  bid_size: number | null;
  ask_size: number | null;
  open_price: string | null;
  high_price: string | null; // 24h/session high (provider or derived)
  low_price: string | null;  // 24h/session low
  close_price: string | null;
  previous_close: string | null;
  change: string | null;
  change_percent: string | null;
  vwap: string | null; // weighted average price
  volume: number | null;
  market_status: "OPEN" | "CLOSED" | "PREMARKET" | "AFTERHOURS" | "HALT";
  data_source: string;
  is_real_time: boolean;
  delay_minutes: number;
  extended_data: {
    signal?: SignalKey;
    stat_value?: string;
    contract_weight?: string;
    signal_weight?: number;
    high_52w?: string | number | null;
    low_52w?: string | number | null;
  } & Record<string, unknown>;
  timestamp: string; // ISO
};

type ApiResponse = {
  rows: MarketData[];
  total: {
    sum_weighted: string;
    avg_weighted: string | null;
    count: number;
    denominator: string;
    as_of: string;
    signal_weight_sum?: number;
    composite_signal?: SignalKey;
    composite_signal_weight?: number;
  };
};

type RoutingFeed = {
  code: string;
  display_name: string;
  connection_type: string;
  provider_key?: string;
  priority: number;
  is_primary: boolean;
};

type RoutingPlanResponse = {
  consumer: {
    code: string;
    display_name: string;
  };
  primary_feed: RoutingFeed | null;
  feeds: RoutingFeed[];
};

type SignalKey =
  | "STRONG_BUY"
  | "BUY"
  | "HOLD"
  | "SELL"
  | "STRONG_SELL";

// ---------------------- Helpers / Utilities ----------------------

function fmt(n: string | number | null | undefined, dp = 2) {
  if (n === null || n === undefined) return "—";
  const num = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(num)) return "—";
  return num.toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

function pctColor(pct: number | null, theme: Theme) {
  if (pct === null) return theme.palette.text.secondary;
  if (pct > 0) return theme.palette.success.main;
  if (pct < 0) return theme.palette.error.main;
  return theme.palette.text.secondary;
}

function signalLabel(sig?: SignalKey) {
  if (!sig) return "—";
  switch (sig) {
    case "STRONG_BUY": return "Strong Buy";
    case "BUY": return "Buy";
    case "HOLD": return "Hold";
    case "SELL": return "Sell";
    case "STRONG_SELL": return "Strong Sell";
  }
}

function signalColor(sig?: SignalKey): ChipProps["color"] {
  if (!sig) return "default";
  switch (sig) {
    case "STRONG_BUY": return "success";
    case "BUY": return "success";
    case "HOLD": return "warning";
    case "SELL": return "error";
    case "STRONG_SELL": return "error";
    default: return "default";
  }
}

// ----------------------------- Mocking ---------------------------

// ----------------------------- UI Pieces -------------------------

//

function SignalBox({sig}:{sig?: SignalKey}){
  return (
    <Chip
      label={signalLabel(sig)}
      color={signalColor(sig)}
      size="small"
      variant="filled"
      sx={{ fontSize: '0.6rem', fontWeight: 'bold' }}
    />
  );
}

type TotalData = ApiResponse["total"];

function TotalCard({totalData, theme}:{totalData: TotalData | null; theme: Theme}){
  const weightedAvg = totalData?.avg_weighted ? Number(totalData.avg_weighted) : null;
  const count = totalData?.count ?? 0;
  const asOf = totalData?.as_of ? new Date(totalData.as_of) : new Date();

  return (
    <motion.div layout initial={{opacity:0, y:8}} animate={{opacity:1, y:0}}>
      <Paper 
        elevation={5} 
        sx={{ 
          height: '100%', 
          overflow: 'hidden',
          borderRadius: 2,
          background: `linear-gradient(135deg, ${theme.palette.warning.main}, ${theme.palette.warning.dark})`,
          border: `2px solid ${theme.palette.warning.light}`
        }}
      >
        {/* Header strip */}
        <Box 
          sx={{ 
            px: 2, 
            py: 1, 
            background: theme.palette.warning.dark,
            color: theme.palette.warning.contrastText,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <Typography variant="body2" fontWeight="bold">TOTAL</Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label="Composite"
              color="warning"
              size="small"
              variant="filled"
              sx={{ fontSize: '0.6rem', fontWeight: 'bold' }}
            />
            <Typography variant="body2" fontWeight="bold">
              {count} Futures
            </Typography>
          </Box>
        </Box>
        {/* Body */}
        <Box p={2}>
          <Box display="flex" gap={2}>
            <Box flex={1}>
              <Typography variant="h4" fontWeight="bold" sx={{ lineHeight: 1.2, color: 'white' }}>
                {weightedAvg ? fmt(weightedAvg, 3) : "—"}
              </Typography>
              <Typography variant="caption" sx={{ mt: 0.5, display: 'block', color: 'rgba(255,255,255,0.8)' }}>
                Weighted Average
              </Typography>

              <Box display="flex" gap={1} sx={{ mt: 2 }}>
                <Box flex={1}>
                  <Paper variant="outlined" sx={{ p: 1, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.1)' }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>Sum</Typography>
                    <Typography variant="body2" fontWeight="medium" color="white">
                      {totalData?.sum_weighted ? fmt(totalData.sum_weighted, 2) : "—"}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Weighted</Typography>
                  </Paper>
                </Box>
                <Box flex={1}>
                  <Paper variant="outlined" sx={{ p: 1, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.1)' }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>Count</Typography>
                    <Typography variant="body2" fontWeight="medium" color="white">{count}</Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Instruments</Typography>
                  </Paper>
                </Box>
              </Box>
            </Box>

            <Box flex={1}>
              <Box 
                height={64} 
                display="flex" 
                flexDirection="column"
                alignItems="center" 
                justifyContent="center"
                sx={{ 
                  background: 'rgba(255,255,255,0.1)', 
                  borderRadius: 1,
                  color: 'white'
                }}
              >
                {totalData?.composite_signal ? (
                  <>
                    <Chip
                      label={signalLabel(totalData.composite_signal)}
                      color={signalColor(totalData.composite_signal)}
                      size="small"
                      variant="filled"
                      sx={{ fontSize: '0.7rem', fontWeight: 'bold' }}
                    />
                    <Typography variant="caption" sx={{ mt: 0.5, color: 'rgba(255,255,255,0.8)' }}>
                      Wgt: {totalData.signal_weight_sum || 0}
                    </Typography>
                  </>
                ) : (
                  <Typography variant="h6" fontWeight="bold">
                    📊 COMPOSITE
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>

          <Box mt={2}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                {asOf.toLocaleTimeString()}
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase' }}>
                LIVE TOTAL
              </Typography>
            </Box>
          </Box>
        </Box>
      </Paper>
    </motion.div>
  );
}

function L1Card({row, onSample, hist: _hist, theme, getQty, setQty}:{
  row: MarketData; 
  onSample:(value:number)=>void; 
  hist:number[]; 
  theme: Theme;
  getQty: (symbol: string) => number;
  setQty: (symbol: string, qty: number) => void;
}){
  const pct = row.change_percent ? Number(row.change_percent) : ((row as any).last_prev_pct != null ? Number((row as any).last_prev_pct) : null);
  const spread = row.bid && row.ask ? Number(row.ask) - Number(row.bid) : null;
  const sig = row.extended_data?.signal as SignalKey | undefined;
  const statValue = row.extended_data?.stat_value;
  const signalWeight = row.extended_data?.signal_weight;
  const netChange = row.change != null ? Number(row.change) : ((row as any).last_prev_diff != null ? Number((row as any).last_prev_diff) : null);

  useEffect(() => { onSample(Number(row.price)); }, [row.price, onSample]);
  // Sparkline data removed

  return (
    <motion.div layout initial={{opacity:0, y:8}} animate={{opacity:1, y:0}}>
      <Paper 
        elevation={3} 
        sx={{ 
          height: '389px',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 2,
          background: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`
        }}
      >
        {/* Header strip: symbol, % change, and the new Signal container */}
        <Box 
          sx={{ 
            px: 2, 
            py: 1, 
            background: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <Typography variant="body2" fontWeight="bold">{row.instrument.symbol}</Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <SignalBox sig={sig} />
            <Typography 
              variant="body2" 
              fontWeight="bold"
              sx={{ 
                color: 'white',
                bgcolor: 'rgba(255,255,255,0.2)',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: '0.75rem'
              }}
            >
              Wgt: {signalWeight || "0"}
            </Typography>
            <Typography 
              variant="body2" 
              fontWeight="bold"
              sx={{ 
                color: 'white',
                bgcolor: 'rgba(255,255,255,0.2)',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: '0.75rem'
              }}
            >
              {statValue ? fmt(statValue, 3) : "—"}
            </Typography>
            <Typography 
              variant="body2" 
              fontWeight="bold"
              sx={{ color: pctColor(pct, theme) }}
            >
              {pct === null ? "—" : `${fmt(pct,2)}%`}
            </Typography>
          </Box>
        </Box>

        {/* Body (scrollable area) */}
        <Box 
          p={2} 
          className="l1-body"
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden'
          }}
        >
          <Box display="flex" gap={2}>
            <Box flex={1}>
              {/* Last on the left, Net Change on the right */}
              <Box display="flex" alignItems="flex-start" justifyContent="space-between" gap={2}>
                <Box>
                  <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
                    {fmt(row.price, row.instrument.display_precision)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Last
                  </Typography>
                </Box>
                <Box textAlign="right">
                  <Box display="flex" alignItems="flex-start" justifyContent="flex-end" gap={1}>
                    <Typography variant="h6" fontWeight="bold" sx={{ color: pctColor(pct, theme), lineHeight: 1 }}>
                      {netChange === null ? '—' : fmt(netChange, row.instrument.display_precision)}
                    </Typography>
                    <Typography variant="subtitle2" fontWeight="bold" sx={{ color: pctColor(pct, theme), lineHeight: 1, mt: '2px' }}>
                      {pct === null ? '—' : `${fmt(pct, 2)}%`}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Change
                  </Typography>
                </Box>
              </Box>

              {/* Bid/Ask Buttons - Red/Green with clickable styling */}
              <Box 
                sx={{ 
                  mt: 0.75,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 1
                }}
              >
                {/* Bid Button (GREEN) */}
                <Box 
                  component="button"
                  onClick={() => {/* Future: handle bid click */}}
                  sx={{ 
                    gridColumn: '1',
                    px: 1,
                    py: 1.2,
                    textAlign: 'center',
                    background: theme.palette.success.dark,
                    border: 'none',
                    borderRadius: 1,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      background: theme.palette.success.main,
                      transform: 'scale(1.02)',
                    }
                  }}
                >
                  <Typography variant="caption" fontWeight="bold" sx={{ color: 'white', display: 'block', mb: 0.5 }}>
                    BID
                  </Typography>
                  <Typography variant="h6" fontWeight="bold" sx={{ color: 'white', lineHeight: 1, fontSize: '1.05rem' }}>
                    {fmt(row.bid, row.instrument.display_precision)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)', display: 'block', mt: 0.35 }}>
                    Size {row.bid_size ?? "—"}
                  </Typography>
                </Box>

                {/* Ask Button (RED) */}
                <Box 
                  component="button"
                  onClick={() => {/* Future: handle ask click */}}
                  sx={{ 
                    gridColumn: '2',
                    px: 1,
                    py: 1.2,
                    textAlign: 'center',
                    background: theme.palette.error.dark,
                    border: 'none',
                    borderRadius: 1,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      background: theme.palette.error.main,
                      transform: 'scale(1.02)',
                    }
                  }}
                >
                  <Typography variant="caption" fontWeight="bold" sx={{ color: 'white', display: 'block', mb: 0.5 }}>
                    ASK
                  </Typography>
                  <Typography variant="h6" fontWeight="bold" sx={{ color: 'white', lineHeight: 1, fontSize: '1.05rem' }}>
                    {fmt(row.ask, row.instrument.display_precision)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)', display: 'block', mt: 0.35 }}>
                    Size {row.ask_size ?? "—"}
                  </Typography>
                </Box>
              </Box>

              {/* Trading Calculator - Always Visible */}
              <Paper 
                variant="outlined" 
                sx={{ 
                  mt: 1, 
                  p: 1.5, 
                  bgcolor: 'rgba(255, 255, 255, 0.02)',
                  borderColor: 'rgba(255, 255, 255, 0.1)'
                }}
              >
                {/* Quantity Selector */}
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                  <Typography variant="caption" fontWeight="medium" color="text.secondary">
                    Qty:
                  </Typography>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setQty(row.instrument.symbol, getQty(row.instrument.symbol) - 1)}
                      sx={{ minWidth: '30px', p: 0.5, fontSize: '0.75rem' }}
                    >
                      −
                    </Button>
                    <Box 
                      sx={{ 
                        px: 2, 
                        py: 0.5, 
                        bgcolor: 'rgba(255,255,255,0.05)', 
                        borderRadius: 1,
                        minWidth: '40px',
                        textAlign: 'center'
                      }}
                    >
                      <Typography variant="body2" fontWeight="bold">
                        {getQty(row.instrument.symbol)}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setQty(row.instrument.symbol, getQty(row.instrument.symbol) + 1)}
                      sx={{ minWidth: '30px', p: 0.5, fontSize: '0.75rem' }}
                    >
                      +
                    </Button>
                  </Box>
                </Box>

                {/* Calculations */}
                <Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                    <Typography variant="caption" color="text.secondary">
                      Qty × Tick 1 =
                    </Typography>
                    <Typography variant="caption" fontWeight="bold" color="primary.main">
                      {row.instrument.tick_value 
                        ? `$${fmt(parseFloat(row.instrument.tick_value) * getQty(row.instrument.symbol), 2)}`
                        : '—'
                      }
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="caption" color="text.secondary">
                      Qty × Margin Req =
                    </Typography>
                    <Typography variant="caption" fontWeight="bold" color="warning.main">
                      {row.instrument.margin_requirement 
                        ? `$${fmt(parseFloat(row.instrument.margin_requirement) * getQty(row.instrument.symbol), 2)}`
                        : '—'
                      }
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              {/* Volume and VWAP Row */}
              <Box 
                sx={{ 
                  mt: 1,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 1
                }}
              >
                <Box sx={{ gridColumn: '1' }}>
                  <Paper variant="outlined" sx={{ p: 1, textAlign: 'center', minHeight: '70px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <Typography variant="caption" color="text.secondary">Volume</Typography>
                    <Typography variant="body2" fontWeight="medium">{fmt(row.volume, 0)}</Typography>
                  </Paper>
                </Box>
                <Box sx={{ gridColumn: '2' }}>
                  <Paper variant="outlined" sx={{ p: 0.5, textAlign: 'center', minHeight: '70px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', lineHeight: 1.2 }}>VWAP</Typography>
                    <Typography variant="body2" fontWeight="medium" sx={{ my: 0.25 }}>{fmt(row.vwap, row.instrument.display_precision)}</Typography>
                    <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem', lineHeight: 1 }}>Spread {fmt(spread, row.instrument.display_precision)}</Typography>
                  </Paper>
                </Box>
              </Box>
            </Box>
          </Box>

          {/* Stats rows - reformatted to header rows with values underneath */}
          <Box mt={2}>
            {/* Row group: Close (prev) and Open */}
            <Box>
              {/* Headers */}
              <Box display="flex" justifyContent="space-between" alignItems="baseline">
                <Typography variant="caption" color="text.secondary">Close</Typography>
                <Typography variant="caption" color="text.secondary">Open</Typography>
              </Box>
              {/* Values */}
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
                <Typography variant="caption" fontWeight="medium">{fmt(row.previous_close, row.instrument.display_precision)}</Typography>
                <Typography variant="caption" fontWeight="medium">{fmt(row.open_price, row.instrument.display_precision)}</Typography>
              </Box>
            </Box>

            {/* Row group: Open vs Previous — number and percent */}
            <Box mt={1}>
              <Box display="flex" justifyContent="space-between" alignItems="baseline">
                <Typography variant="caption" color="text.secondary">Open vs Prev (Number)</Typography>
                <Typography variant="caption" color="text.secondary">Open vs Prev (%)</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
                <Typography variant="caption" fontWeight="medium">{fmt((row as any).open_prev_diff as any, row.instrument.display_precision)}</Typography>
                <Typography variant="caption" fontWeight="medium">{`${fmt((row as any).open_prev_pct as any, 2)}%`}</Typography>
              </Box>
            </Box>

            {/* Row group: 24 hour Low/High */}
            <Box mt={1}>
              <Box display="flex" justifyContent="space-between" alignItems="baseline">
                <Typography variant="caption" color="text.secondary">24 hour Low</Typography>
                <Typography variant="caption" color="text.secondary">24 hour High</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
                <Typography variant="caption" fontWeight="medium">{fmt(row.low_price, row.instrument.display_precision)}</Typography>
                <Typography variant="caption" fontWeight="medium">{fmt(row.high_price, row.instrument.display_precision)}</Typography>
              </Box>
            </Box>

            {/* Row group: Range number and percent */}
            <Box mt={1}>
              <Box display="flex" justifyContent="space-between" alignItems="baseline">
                <Typography variant="caption" color="text.secondary">Range (High - Low)</Typography>
                <Typography variant="caption" color="text.secondary">Range % (vs Prev)</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
                <Typography variant="caption" fontWeight="medium">{fmt((row as any).range_diff as any)}</Typography>
                <Typography variant="caption" fontWeight="medium">{fmt((row as any).range_pct as any)}</Typography>
              </Box>
            </Box>

            {/* Row group: 52-week Low/High */}
            <Box mt={1}>
              <Box display="flex" justifyContent="space-between" alignItems="baseline">
                <Typography variant="caption" color="text.secondary">52-week Low</Typography>
                <Typography variant="caption" color="text.secondary">52-week High</Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
                <Typography variant="caption" fontWeight="medium">{fmt((row.extended_data as any)?.low_52w as any, row.instrument.display_precision)}</Typography>
                <Typography variant="caption" fontWeight="medium">{fmt((row.extended_data as any)?.high_52w as any, row.instrument.display_precision)}</Typography>
              </Box>
            </Box>

            <Box display="flex" justifyContent="space-between" mt={1} mb={2}>
              <Typography variant="caption" color="text.disabled">
                {new Date(row.timestamp).toLocaleTimeString()}
              </Typography>
              <Typography variant="caption" color="text.disabled" sx={{ textTransform: 'uppercase' }}>
                {row.market_status}
              </Typography>
            </Box>
          </Box>
        </Box>
      </Paper>
    </motion.div>
  );
}

// -------------------------- Main Component -----------------------

export default function FutureTrading(){
  const theme = useTheme();
  const [pollMs, setPollMs] = useState(2000);
  const [rows, setRows] = useState<MarketData[]>([]);
  const [totalData, setTotalData] = useState<TotalData | null>(null);
  const [routingPlan, setRoutingPlan] = useState<RoutingPlanResponse | null>(null);
  const [routingError, setRoutingError] = useState<string | null>(null);
  const [routingLoading, setRoutingLoading] = useState(true);
  
  // Quantity state for each instrument (symbol -> quantity)
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  
  // Helper to get/set quantity for an instrument
  const getQty = (symbol: string) => quantities[symbol] || 1;
  const setQty = (symbol: string, qty: number) => {
    setQuantities(prev => ({ ...prev, [symbol]: Math.max(1, qty) }));
  };

  // sparkline buffers
  const seriesRef = useRef<Record<string, number[]>>({});
  const getSeries = (sym:string) => (seriesRef.current[sym] ||= []);

  // Routing is no longer needed - we fetch directly from TOS Excel via LiveData
  // Set routing to success state immediately
  useEffect(() => {
    setRoutingLoading(false);
    setRoutingError(null);
    setRoutingPlan({ 
      consumer: 'futures_trading', 
      provider: 'tos_excel', 
      status: 'active',
      primary_feed: {
        code: 'TOS_RTD',
        display_name: 'TOS Excel RTD'
      }
    } as any);
  }, []);

  async function fetchQuotes(){
    // Use FutureTrading endpoint (fetches from TOS and enriches with signals)
    const endpoint = "/api/quotes/latest?consumer=futures_trading";

    try {
      const r = await fetch(endpoint);
      if (r.ok) {
        const data: ApiResponse = await r.json();
        setRows(data.rows);
        setTotalData(data.total);
        return;
      } else {
        throw new Error(`Request failed with status ${r.status}`);
      }
    } catch (error) {
      console.error(`Failed to fetch quotes:`, error);
      throw new Error("Quote endpoint failed");
    }
  }

  useEffect(()=>{
    (async()=>{
      try{
        if (!routingError) {
          await fetchQuotes();
        }
      }catch{
        // Create empty containers for all 11 futures but with no data
        const emptyContainers = FUTURES_11.map((symbol, index) => ({
          instrument: {
            id: index + 1,
            symbol: symbol,
            name: symbol,
            exchange: "—",
            currency: "USD",
            display_precision: 2,
            tick_value: null,
            margin_requirement: null,
            is_active: true,
            sort_order: index
          },
          price: "—",
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
          market_status: "CLOSED" as const,
          data_source: "none",
          is_real_time: false,
          delay_minutes: 0,
          extended_data: {},
          timestamp: new Date().toISOString()
        }));
        setRows(emptyContainers);
      }
    })();
  },[routingError]);

  useEffect(()=>{
    // Poll for updates
    const id = setInterval(()=>{ fetchQuotes().catch(()=>{}); }, pollMs);
    return ()=> clearInterval(id);
  },[pollMs]);

  const effective = rows;
  const currentTotalData = totalData;

  // Helper to create an empty placeholder row for missing symbols
  function makeEmptyRow(symbol: string, index: number): MarketData {
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
      price: "—",
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
      data_source: "none",
      is_real_time: false,
      delay_minutes: 0,
      extended_data: {},
      timestamp: new Date().toISOString(),
    };
  }

  // Filter to our 11 futures and order exactly as FUTURES_11, padding with placeholders for missing ones
  const ordered: MarketData[] = useMemo(()=>{
    // Normalize symbols by removing leading slash for comparison
    const normalizeSymbol = (s: string) => s.replace(/^\//, '');
    const map = new Map(effective.map(r => [normalizeSymbol(r.instrument.symbol), r]));
    return FUTURES_11.map((sym: string, idx: number) => {
      const normalized = normalizeSymbol(sym);
      return map.get(normalized) ?? makeEmptyRow(sym, idx);
    });
  }, [effective]);

  // Always display 11 cards in the configured order
  const displayRows: MarketData[] = useMemo(()=> ordered, [ordered]);

  const onSample = (sym:string) => (n:number)=>{
    const buf = getSeries(sym); buf.push(n); if(buf.length>60) buf.shift();
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
        <Box mb={2}>
          <Typography variant="caption" color="text.secondary">
            Feed: {routingPlan.primary_feed?.display_name ?? "Not configured"}
          </Typography>
        </Box>
      )}

      <Box display="flex" justifyContent="flex-end" alignItems="center" mb={3}>
        <Button
          variant="outlined"
          onClick={()=> setPollMs(p=> p===2000?1000 : p===1000?5000 : 2000)}
          startIcon={<RefreshCw size={16} />}
          title="Toggle polling interval"
          sx={{ 
            borderColor: 'white', 
            color: 'white',
            '&:hover': {
              borderColor: 'rgba(255, 255, 255, 0.8)',
              backgroundColor: 'rgba(255, 255, 255, 0.1)'
            }
          }}
        >
          {pollMs/1000}s
        </Button>
      </Box>

      {/* Responsive grid layout - TOTAL card + 11 futures cards */}
      <Box 
        display="grid" 
        gridTemplateColumns={{
          xs: 'repeat(1, 1fr)',
          sm: 'repeat(2, 1fr)', 
          md: 'repeat(3, 1fr)',
          lg: 'repeat(4, 1fr)',
          xl: 'repeat(6, 1fr)'
        }}
        gap={2}
      >
        {/* Total Composite Card - appears first */}
        <Box>
          <TotalCard 
            totalData={currentTotalData}
            theme={theme}
          />
        </Box>

        {/* Individual Futures Cards */}
        {displayRows.slice(0, 11).map(row => (
          <Box key={row.instrument.symbol}>
            <L1Card 
              row={row}
              onSample={onSample(row.instrument.symbol)}
              hist={getSeries(row.instrument.symbol)}
              theme={theme}
              getQty={getQty}
              setQty={setQty}
            />
          </Box>
        ))}
      </Box>
    </Container>
  );
}