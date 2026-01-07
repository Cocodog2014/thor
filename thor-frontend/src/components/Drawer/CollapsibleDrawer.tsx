import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useWebSocket from 'react-use-websocket';
import {
  Drawer,
  Toolbar,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Box,
  Typography,
  Divider,
  TextField,
 
  CircularProgress,
  Grid,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';

// --- Constants & Helpers ---
export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;
const MIN_DRAWER_WIDTH = 200;
const MAX_DRAWER_WIDTH = 600;

const getWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
  return `${protocol}//${host}/ws/`;
};

const normalizeWsSymbol = (s: unknown) => {
  if (typeof s !== 'string') return '';
  return s.replace(/^\/+/, '').toUpperCase().trim();
};
const toNumeric = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') {
    return undefined;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : undefined;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return undefined;

    const suffix = trimmed.slice(-1).toLowerCase();
    let multiplier = 1;
    let numericPortion = trimmed;

    if (suffix === 'k' || suffix === 'm' || suffix === 'b') {
      numericPortion = trimmed.slice(0, -1);
      if (suffix === 'k') multiplier = 1e3;
      if (suffix === 'm') multiplier = 1e6;
      if (suffix === 'b') multiplier = 1e9;
    }

    const parsed = Number(numericPortion);
    if (Number.isNaN(parsed)) {
      return undefined;
    }
    return parsed * multiplier;
  }
  return undefined;
};

const formatPrice = (v?: number) => (v !== undefined ? v.toFixed(2) : '-');
const formatVolume = (v?: number) => {
  if (v === undefined) return '-';
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}b`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}m`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
  return v.toString();
};

type MetricKey = 'last' | 'bid' | 'ask' | 'volume' | 'open' | 'high' | 'low' | 'close';
type Direction = 'up' | 'down' | null;

type QuoteMetrics = Partial<Record<MetricKey, number>>;
type MarketDataMap = Record<string, QuoteMetrics>;

type WatchlistItem = {
  instrument?: {
    symbol?: string;
  };
};

const METRIC_CONFIG: Array<{
  key: MetricKey;
  label: string;
  formatter: (value?: number) => string;
  highlight?: boolean;
}> = [
  { key: 'last', label: 'Last', formatter: formatPrice, highlight: true },
  { key: 'bid', label: 'Bid', formatter: formatPrice },
  { key: 'ask', label: 'Ask', formatter: formatPrice },
  { key: 'volume', label: 'Vol', formatter: formatVolume },
  { key: 'open', label: 'Open', formatter: formatPrice },
  { key: 'high', label: 'High', formatter: formatPrice },
  { key: 'low', label: 'Low', formatter: formatPrice },
  { key: 'close', label: 'Close', formatter: formatPrice },
];

const METRIC_KEYS: MetricKey[] = METRIC_CONFIG.map((cfg) => cfg.key);

// --- Sub-components ---

interface WatchlistItemRowProps {
  symbol: string;
  data?: QuoteMetrics;
  onRemove: (symbol: string) => void;
}

const WatchlistItemRow: React.FC<WatchlistItemRowProps> = ({ symbol, data, onRemove }) => {
  const prevValues = useRef<Record<MetricKey, number | undefined>>(
    METRIC_KEYS.reduce(
      (acc, key) => ({ ...acc, [key]: undefined }),
      {} as Record<MetricKey, number | undefined>
    )
  );
  const resetTimers = useRef<Record<MetricKey, number | undefined>>(
    METRIC_KEYS.reduce(
      (acc, key) => ({ ...acc, [key]: undefined }),
      {} as Record<MetricKey, number | undefined>
    )
  );
  const [directions, setDirections] = useState<Record<MetricKey, Direction>>(
    METRIC_KEYS.reduce((acc, key) => ({ ...acc, [key]: null }), {} as Record<MetricKey, Direction>)
  );

  useEffect(() => {
    const pendingUpdates: MetricKey[] = [];
    setDirections((prev) => {
      const next = { ...prev };
      METRIC_KEYS.forEach((key) => {
        const raw = data?.[key];
        const current = typeof raw === 'number' ? raw : undefined;
        const previous = prevValues.current[key];

        if (current === undefined) {
          next[key] = null;
          return;
        }

        if (previous !== undefined) {
          if (current > previous) {
            next[key] = 'up';
            pendingUpdates.push(key);
          } else if (current < previous) {
            next[key] = 'down';
            pendingUpdates.push(key);
          }
        }

        prevValues.current[key] = current;
      });
      return next;
    });

    pendingUpdates.forEach((key) => {
      const existing = resetTimers.current[key];
      if (existing !== undefined) {
        window.clearTimeout(existing);
      }
      resetTimers.current[key] = window.setTimeout(() => {
        setDirections((prev) => ({ ...prev, [key]: null }));
        resetTimers.current[key] = undefined;
      }, 800);
    });
  }, [data]);

  useEffect(() => () => {
    METRIC_KEYS.forEach((key) => {
      const timer = resetTimers.current[key];
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    });
  }, []);

  const metrics = useMemo(
    () =>
      METRIC_CONFIG.map(({ key, label, formatter, highlight }) => {
        const raw = data?.[key];
        const numeric = typeof raw === 'number' ? raw : undefined;
        return {
          key,
          label,
          value: formatter(numeric),
          highlight: Boolean(highlight),
          direction: directions[key],
        };
      }),
    [directions, data]
  );

  return (
    <Box className="thor-watchlist-item" sx={{ p: 1.5, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#1976d2' }}>{symbol}</Typography>
        <IconButton size="small" onClick={() => onRemove(symbol)}><CloseIcon fontSize="inherit" /></IconButton>
      </Box>
      <Grid container spacing={1}>
        {metrics.map((m) => (
          <Grid item xs={3} key={m.key}>
            <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary', textTransform: 'uppercase' }}>{m.label}</Typography>
            <Typography sx={{ 
              fontSize: '0.75rem', 
              fontWeight: m.highlight ? 'bold' : 'normal',
              color: m.direction === 'up' ? 'success.main' : m.direction === 'down' ? 'error.main' : 'text.primary',
              transition: 'color 0.3s'
            }}>
              {m.value}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

// --- Main Component ---

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
}

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [drawerWidth, setDrawerWidth] = useState(widthOpen);
  const [isResizing, setIsResizing] = useState(false);
  const resizeState = useRef({ startX: 0, startWidth: drawerWidth });

  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [marketData, setMarketData] = useState<MarketDataMap>({});
  const [query, setQuery] = useState('');

  const { lastJsonMessage } = useWebSocket(getWsUrl(), { shouldReconnect: () => true, share: true });

  // WebSocket Logic
  const applyMarketPatch = useCallback((symbolRaw: unknown, patch: Record<string, unknown>) => {
    const symbol = normalizeWsSymbol(symbolRaw);
    if (!symbol) return;
    setMarketData((prev) => {
      const current = prev[symbol] || {};
      const next = { ...current };
      let changed = false;
      Object.keys(patch).forEach((key) => {
        const val = toNumeric(patch[key]);
        if (val !== undefined && next[key] !== val) {
          next[key] = val;
          changed = true;
        }
      });
      return changed ? { ...prev, [symbol]: next } : prev;
    });
  }, []);

  useEffect(() => {
    if (!lastJsonMessage) return;
    const msg = lastJsonMessage as { type?: unknown; data?: unknown };
    const msgType = typeof msg.type === 'string' ? msg.type : '';
    const msgData = (msg.data && typeof msg.data === 'object') ? (msg.data as Record<string, unknown>) : undefined;
    switch (msgType) {
      case 'quote_tick':
        applyMarketPatch(msgData?.symbol, {
          bid: msgData?.bid,
          ask: msgData?.ask,
          last: msgData?.last ?? msgData?.price,
          volume: msgData?.volume,
        });
        break;
      case 'market.24h':
        if (msgData) {
          applyMarketPatch(msgData.symbol, msgData);
        }
        break;
      case 'market_data': {
        const quotesRaw = msgData?.quotes;
        const quotes = Array.isArray(quotesRaw) ? quotesRaw : [];
        quotes.forEach((quote) => {
          if (!quote || typeof quote !== 'object') return;
          const q = quote as Record<string, unknown>;
          applyMarketPatch(q.symbol ?? q.SYMBOL, {
            bid: q.bid ?? q.Bid,
            ask: q.ask ?? q.Ask,
            last: q.last ?? q.price ?? q.Last,
            open: q.open ?? q.open_price ?? q.Open,
            high: q.high ?? q.high_price ?? q.High,
            low: q.low ?? q.low_price ?? q.Low,
            close: q.close ?? q.close_price ?? q.Close,
            volume: q.volume ?? q.Volume,
          });
        });
        break;
      }
    }
  }, [lastJsonMessage, applyMarketPatch]);

  // Resize Logic
  const handleResizeMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true);
    resizeState.current = { startX: e.clientX, startWidth: drawerWidth };
  };

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: MouseEvent) => {
      const delta = e.clientX - resizeState.current.startX;
      setDrawerWidth(Math.min(MAX_DRAWER_WIDTH, Math.max(MIN_DRAWER_WIDTH, resizeState.current.startWidth + delta)));
    };
    const onUp = () => setIsResizing(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [isResizing]);

  // Actions
  const loadWatchlist = async () => {
    setWatchlistLoading(true);
    try {
      const res = await api.get('/instruments/watchlist/');
      setWatchlist(res.data?.items || []);
    } catch (err: unknown) {
      console.error('Failed to load watchlist', err);
      setWatchlist([]);
    }
    finally { setWatchlistLoading(false); }
  };

  const removeSymbol = async (symbol: string) => {
    const next = watchlist.filter((w) => (w.instrument?.symbol || '').toUpperCase() !== symbol);
    setWatchlist(next);
    await api.put('/instruments/watchlist/', { items: next.map((item, i) => ({ symbol: item.instrument.symbol, order: i })) });
  };

  useEffect(() => { if (open) loadWatchlist(); }, [open]);

  const signOut = () => { logout(); sessionStorage.removeItem(HOME_WELCOME_DISMISSED_KEY); navigate('/auth/login'); };

  const currentWidth = open ? drawerWidth : widthClosed;

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: currentWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: currentWidth,
          overflow: 'hidden',
          transition: isResizing ? 'none' : 'width 0.2s',
          backgroundColor: '#000',
        },
      }}
    >
      <Toolbar sx={{ justifyContent: 'center' }}>
        <IconButton onClick={onToggle}>{open ? <ChevronLeftIcon /> : <ChevronRightIcon />}</IconButton>
      </Toolbar>

      {open && (
        <Box sx={{ flexGrow: 1, overflowY: 'auto', px: 2 }}>
          {/* Account Info */}
          <Typography variant="subtitle2" sx={{ color: 'primary.main', mb: 1 }}>Account Info</Typography>
          <Box sx={{ fontSize: '0.75rem', color: 'text.secondary', mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Net Liq</span>
              <Box component="span" sx={{ color: '#4caf50' }}>$86,081.37</Box>
            </Box>
          </Box>
          <Divider sx={{ mb: 2 }} />

          {/* Watchlist */}
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Watchlist</Typography>
          <TextField 
            size="small" fullWidth placeholder="Add symbol" 
            value={query} onChange={(e) => setQuery(e.target.value)}
            sx={{ mb: 2 }}
          />
          
          <Box>
            {watchlistLoading ? <CircularProgress size={20} /> : 
              watchlist.map((w) => {
                const rawSymbol = (w.instrument?.symbol || '').toUpperCase();
                const key = normalizeWsSymbol(rawSymbol);
                const data = marketData[key];
                return <WatchlistItemRow key={rawSymbol} symbol={rawSymbol} data={data} onRemove={removeSymbol} />;
              })
            }
          </Box>
        </Box>
      )}

      <Box sx={{ mt: 'auto' }}>
        <Divider />
        <List>
          <ListItem disablePadding>
            <ListItemButton onClick={signOut}>
              <ListItemIcon><LogoutIcon /></ListItemIcon>
              {open && <ListItemText primary="Sign out" />}
            </ListItemButton>
          </ListItem>
        </List>
      </Box>

      {open && (
        <Box
          onMouseDown={handleResizeMouseDown}
          sx={{
            position: 'absolute', right: 0, top: 0, bottom: 0, width: 5,
            cursor: 'col-resize', '&:hover': { bgcolor: 'primary.main' }
          }}
        />
      )}
    </Drawer>
  );
};

export default CollapsibleDrawer;