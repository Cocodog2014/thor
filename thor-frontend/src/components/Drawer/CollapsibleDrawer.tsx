import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 1. Remove the 'react-use-websocket' import
// import useWebSocket from 'react-use-websocket'; 
import { useWsMessage } from '../../realtime'; // <--- Use this instead
import type { WsEnvelope } from '../../realtime/types';
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
  Button,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';

// --- Constants & Helpers ---
export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;
const MIN_DRAWER_WIDTH = 200;
const MAX_DRAWER_WIDTH = 600;

const navigationItems = [
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

const normalizeWsSymbol = (s: unknown) => {
  if (typeof s !== 'string') return '';
  return s.replace(/^\/+/, '').toUpperCase().trim();
};

const toNumeric = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') return undefined;
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return undefined;
    const suffix = trimmed.slice(-1).toLowerCase();
    let multiplier = 1;
    let numericPortion = trimmed;
    if (suffix === 'k') { multiplier = 1e3; numericPortion = trimmed.slice(0, -1); }
    else if (suffix === 'm') { multiplier = 1e6; numericPortion = trimmed.slice(0, -1); }
    else if (suffix === 'b') { multiplier = 1e9; numericPortion = trimmed.slice(0, -1); }
    const parsed = Number(numericPortion);
    return Number.isNaN(parsed) ? undefined : parsed * multiplier;
  }
  return undefined;
};

const formatPrice = (v?: number) => (v !== undefined ? v.toFixed(2) : '-');
const formatVolume = (v?: number) => {
  if (v === undefined) return '-';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}b`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}m`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return v.toString();
};

type MetricKey = 'last' | 'bid' | 'ask' | 'volume' | 'open' | 'high' | 'low' | 'close';
type MarketDataMap = Record<string, Partial<Record<MetricKey, number>>>;

interface WatchlistItemRowProps {
  symbol: string;
  data?: Partial<Record<MetricKey, number>>;
  onRemove: (symbol: string) => void;
}

const WatchlistItemRow: React.FC<WatchlistItemRowProps> = ({ symbol, data, onRemove }) => {
  const prevLast = useRef<number | undefined>(undefined);
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);

  useEffect(() => {
    const current = data?.last;
    if (current !== undefined && prevLast.current !== undefined && current !== prevLast.current) {
      setFlash(current > prevLast.current ? 'up' : 'down');
      const timer = setTimeout(() => setFlash(null), 800);
      return () => clearTimeout(timer);
    }
    if (current !== undefined) prevLast.current = current;
  }, [data?.last]);

  const priceColor = flash === 'up' ? '#4caf50' : flash === 'down' ? '#f44336' : 'inherit';

  return (
    <Box className="thor-watchlist-item" sx={{ p: 1.5, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#1976d2' }}>{symbol}</Typography>
        <IconButton size="small" onClick={() => onRemove(symbol)}><CloseIcon fontSize="inherit" /></IconButton>
      </Box>
      <Grid container spacing={1}>
        <Grid item xs={3}>
          <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>LAST</Typography>
          <Typography sx={{ fontSize: '0.75rem', fontWeight: 'bold', color: priceColor, transition: 'color 0.3s' }}>
            {formatPrice(data?.last)}
          </Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>BID</Typography>
          <Typography sx={{ fontSize: '0.75rem' }}>{formatPrice(data?.bid)}</Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>ASK</Typography>
          <Typography sx={{ fontSize: '0.75rem' }}>{formatPrice(data?.ask)}</Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>VOL</Typography>
          <Typography sx={{ fontSize: '0.75rem' }}>{formatVolume(data?.volume)}</Typography>
        </Grid>
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

  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [marketData, setMarketData] = useState<MarketDataMap>({});
  const [query, setQuery] = useState('');

  // ---------------------------------------------------------------------------
  // 2. UNIFIED WEBSOCKET LOGIC (Stable!)
  // ---------------------------------------------------------------------------
  const applyMarketPatch = useCallback((symbolRaw: unknown, patch: Partial<Record<MetricKey, unknown>>) => {
    const symbol = normalizeWsSymbol(symbolRaw);
    if (!symbol) return;
    setMarketData((prev) => {
      const current = prev[symbol] || {};
      const next = { ...current };
      let changed = false;
      (Object.entries(patch) as Array<[MetricKey, unknown]>).forEach(([key, raw]) => {
        const val = toNumeric(raw);
        if (val !== undefined && next[key] !== val) {
          next[key] = val;
          changed = true;
        }
      });
      return changed ? { ...prev, [symbol]: next } : prev;
    });
  }, []);

  // Use the shared global socket connection
  useWsMessage('quote_tick', (msg: WsEnvelope<any>) => {
    applyMarketPatch(msg.data?.symbol, {
      bid: msg.data?.bid,
      ask: msg.data?.ask,
      last: msg.data?.last ?? msg.data?.price,
      volume: msg.data?.volume,
    });
  });

  useWsMessage('market.24h', (msg: WsEnvelope<any>) => {
    applyMarketPatch(msg.data?.symbol, {
      open: msg.data?.open ?? msg.data?.open_price,
      high: msg.data?.high ?? msg.data?.high_price,
      low: msg.data?.low ?? msg.data?.low_price,
      close: msg.data?.close ?? msg.data?.close_price,
      volume: msg.data?.volume,
    });
  });

  // ---------------------------------------------------------------------------
  // RESIZE & DRAWER LOGIC
  // ---------------------------------------------------------------------------
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
    } catch (err) {
      console.error(err);
    } finally { setWatchlistLoading(false); }
  };

  const addSymbol = async (symbolRaw: string) => {
    if (!symbolRaw) return;
    // Optimistic UI update
    const sym = symbolRaw.toUpperCase();
    const next = [...watchlist, { instrument: { symbol: sym } }];
    setWatchlist(next);
    setQuery('');
    try {
      await api.put('/instruments/watchlist/', { items: next.map((item, i) => ({ symbol: item.instrument.symbol, order: i })) });
      loadWatchlist(); 
    } catch (e) { console.error(e); }
  };

  const removeSymbol = async (symbol: string) => {
    const next = watchlist.filter(w => w.instrument?.symbol.toUpperCase() !== symbol);
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
          <Typography variant="subtitle2" sx={{ color: 'primary.main', mb: 1 }}>Account Info</Typography>
          <Box sx={{ fontSize: '0.75rem', color: 'text.secondary', mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Net Liq</span>
              <Box component="span" sx={{ color: '#4caf50' }}>$86,081.37</Box>
            </Box>
          </Box>
          <Divider sx={{ mb: 2 }} />

          <Typography variant="subtitle2" sx={{ mb: 1 }}>Watchlist</Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField 
              size="small" fullWidth placeholder="Add symbol" 
              value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addSymbol(query); }}
            />
            <Button variant="outlined" size="small" onClick={() => addSymbol(query)} disabled={!query.trim()}>Add</Button>
          </Box>
          
          <Box>
            {watchlistLoading ? <CircularProgress size={20} /> : 
              watchlist.map((w) => {
                const sym = (w.instrument?.symbol || '').toUpperCase();
                return <WatchlistItemRow key={sym} symbol={sym} data={marketData[sym]} onRemove={removeSymbol} />;
              })
            }
          </Box>
        </Box>
      )}

      <Box sx={{ mt: 'auto' }}>
        <Divider />
        <List>
          {navigationItems.map((item) => (
             <ListItem key={item.text} disablePadding>
               <ListItemButton onClick={() => window.open(item.path, '_blank')}>
                 <ListItemIcon>{item.icon}</ListItemIcon>
                 {open && <ListItemText primary={item.text} />}
               </ListItemButton>
             </ListItem>
          ))}
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