import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  Button,
  CircularProgress,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
}

export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;
export const MIN_DRAWER_WIDTH = 220;
export const MAX_DRAWER_WIDTH = 440;

const navigationItems = [
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

type InstrumentSummary = {
  id: number;
  symbol: string;
  asset_type: string;
  name?: string;
  exchange?: string;
  currency?: string;
  is_active?: boolean;
};

type WatchlistItem = {
  instrument: InstrumentSummary;
  enabled: boolean;
  stream: boolean;
  order: number;
};

type MarketData = {
  bid?: number;
  ask?: number;
  last?: number;
  volume?: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
};

const getWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
  return `${protocol}//${host}/ws/market-data/`;
};

const WatchlistItemRow: React.FC<{
  symbol: string;
  data: MarketData;
  onRemove: (sym: string) => void;
}> = ({ symbol, data, onRemove }) => {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);
  const prevLast = useRef<number | undefined>(undefined);

  const formatPrice = (value: number | undefined) =>
    value === undefined || value === null ? '-' : value.toFixed(2);

  const formatVolume = (value: number | undefined) => {
    if (value === undefined || value === null) return '-';
    if (Math.abs(value) >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(1)}m`;
    }
    if (Math.abs(value) >= 1_000) {
      return `${(value / 1_000).toFixed(1)}k`;
    }
    return value.toString();
  };

  useEffect(() => {
    if (data.last !== undefined && prevLast.current !== undefined) {
      if (data.last > prevLast.current) {
        setFlash('up');
      } else if (data.last < prevLast.current) {
        setFlash('down');
      }
      const timer = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timer);
    }
    prevLast.current = data.last;
  }, [data.last]);

  const priceColor = flash === 'up' ? '#4caf50' : flash === 'down' ? '#f44336' : 'text.primary';

  const metrics = useMemo(
    () => [
      {
        key: 'last',
        label: 'Last',
        value: formatPrice(data.last),
        highlight: true,
      },
      {
        key: 'bid',
        label: 'Bid',
        value: formatPrice(data.bid),
      },
      {
        key: 'ask',
        label: 'Ask',
        value: formatPrice(data.ask),
      },
      {
        key: 'volume',
        label: 'Volume',
        value: formatVolume(data.volume),
      },
      {
        key: 'open',
        label: 'Open',
        value: formatPrice(data.open),
      },
      {
        key: 'high',
        label: 'High',
        value: formatPrice(data.high),
      },
      {
        key: 'low',
        label: 'Low',
        value: formatPrice(data.low),
      },
      {
        key: 'close',
        label: 'Prev Close',
        value: formatPrice(data.close),
      },
    ],
    [data.close, data.high, data.last, data.low, data.ask, data.bid, data.open, data.volume]
  );

  return (
    <Box className="thor-watchlist-item" sx={{ flexDirection: 'column', alignItems: 'flex-start', py: 1, gap: 0.5, height: 'auto' }}>
      <Box sx={{ display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="thor-watchlist-symbol">{symbol}</span>
        <IconButton size="small" onClick={() => onRemove(symbol)} aria-label={`Remove ${symbol}`}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
      <Box
        sx={{
          width: '100%',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(88px, 1fr))',
          gap: 0.5,
          fontSize: '0.72rem',
          color: 'text.secondary',
        }}
      >
        {metrics.map(({ key, label, value, highlight }) => (
          <Box key={key} sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
            <Box component="span" sx={{ textTransform: 'uppercase', letterSpacing: 0.4 }}>
              {label}
            </Box>
            <Box
              component="span"
              sx={{
                fontWeight: highlight ? 600 : 500,
                color: highlight ? priceColor : 'text.primary',
                fontSize: highlight ? '0.9rem' : '0.78rem',
                transition: 'color 0.3s ease',
              }}
            >
              {value}
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [drawerWidth, setDrawerWidth] = useState(() => {
    const initial = Number(widthOpen) || DEFAULT_WIDTH_OPEN;
    return Math.min(MAX_DRAWER_WIDTH, Math.max(MIN_DRAWER_WIDTH, initial));
  });
  const [isResizing, setIsResizing] = useState(false);
  const resizeState = useRef({ startX: 0, startWidth: drawerWidth });

  const clampWidth = useCallback(
    (value: number) => Math.min(MAX_DRAWER_WIDTH, Math.max(MIN_DRAWER_WIDTH, value)),
    []
  );

  useEffect(() => {
    setDrawerWidth((prev) => {
      const target = Number(widthOpen) || prev;
      return clampWidth(target);
    });
  }, [widthOpen, clampWidth]);

  useEffect(() => {
    if (!isResizing) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      const delta = event.clientX - resizeState.current.startX;
      const nextWidth = clampWidth(resizeState.current.startWidth + delta);
      setDrawerWidth(nextWidth);
    };

    const endResize = () => {
      setIsResizing(false);
    };

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', endResize);

    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', endResize);
    };
  }, [isResizing, clampWidth]);

  useEffect(() => {
    if (!open) return;
    setDrawerWidth((prev) => clampWidth(prev));
  }, [open, clampWidth]);

  const handleResizeMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!open) {
      return;
    }
    resizeState.current = {
      startX: event.clientX,
      startWidth: drawerWidth,
    };
    setIsResizing(true);
    event.preventDefault();
  };

  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  
  const [marketData, setMarketData] = useState<Record<string, MarketData>>({});
  
  const { lastJsonMessage } = useWebSocket(getWsUrl(), {
    shouldReconnect: () => true,
    share: true,
  });

  useEffect(() => {
    if (lastJsonMessage) {
      console.log("WS Frame:", lastJsonMessage);
      const msg = lastJsonMessage as any;
      const symbolRaw = msg.data?.symbol;
      if (symbolRaw) {
        const symbol = symbolRaw.toUpperCase();
        if (msg.type === 'quote_tick' && msg.data) {
          const { bid, ask, last, volume } = msg.data;
          setMarketData((prev) => ({
            ...prev,
            [symbol]: { ...prev[symbol], bid, ask, last, volume },
          }));
        } else if (msg.type === 'market.24h' && msg.data) {
          const { open, high, low, close, volume } = msg.data;
           setMarketData((prev) => ({
            ...prev,
            [symbol]: { ...prev[symbol], open, high, low, close, volume },
          }));
        }
      }
    }
  }, [lastJsonMessage]);

  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<InstrumentSummary[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const suggestionsReqId = useRef(0);

  const normalizedSymbols = useMemo(() => {
    return new Set(watchlist.map((w) => (w.instrument?.symbol ?? '').toUpperCase()));
  }, [watchlist]);

  const loadWatchlist = async () => {
    setWatchlistLoading(true);
    setWatchlistError(null);
    try {
      const res = await api.get('/instruments/watchlist/');
      const items = (res.data?.items ?? []) as WatchlistItem[];
      setWatchlist(Array.isArray(items) ? items : []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load watchlist';
      setWatchlistError(message);
    } finally {
      setWatchlistLoading(false);
    }
  };

  const saveWatchlist = async (items: WatchlistItem[]) => {
    const payload = {
      items: items.map((item, idx) => ({
        instrument_id: item.instrument?.id || undefined,
        symbol: item.instrument?.symbol,
        enabled: item.enabled ?? true,
        stream: item.stream ?? true,
        order: idx,
      })),
    };

    const res = await api.put('/instruments/watchlist/', payload);
    const next = (res.data?.items ?? []) as WatchlistItem[];
    setWatchlist(Array.isArray(next) ? next : items);
  };

  const addSymbol = async (symbolRaw: string) => {
    const symbol = symbolRaw.trim().toUpperCase();
    if (!symbol) return;
    if (normalizedSymbols.has(symbol)) {
      setQuery('');
      setSuggestions([]);
      return;
    }

    const next = watchlist.concat([
      {
        instrument: { id: 0, symbol, asset_type: symbol.startsWith('/') ? 'FUTURE' : 'EQUITY' },
        enabled: true,
        stream: true,
        order: watchlist.length,
      },
    ]);

    setWatchlistError(null);
    setWatchlist(next);
    setQuery('');
    setSuggestions([]);

    try {
      await saveWatchlist(next);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save watchlist';
      setWatchlistError(message);
      void loadWatchlist();
    }
  };

  const removeSymbol = async (symbolRaw: string) => {
    const symbol = symbolRaw.trim().toUpperCase();
    if (!symbol) return;
    const next = watchlist.filter((w) => (w.instrument?.symbol ?? '').toUpperCase() !== symbol);
    setWatchlistError(null);
    setWatchlist(next);
    try {
      await saveWatchlist(next);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save watchlist';
      setWatchlistError(message);
      void loadWatchlist();
    }
  };

  useEffect(() => {
    if (!open) return;
    void loadWatchlist();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 1) {
      setSuggestions([]);
      return;
    }

    const reqId = ++suggestionsReqId.current;
    setSuggestionsLoading(true);

    const handle = window.setTimeout(async () => {
      try {
        const res = await api.get('/instruments/catalog/', { params: { q } });
        if (suggestionsReqId.current !== reqId) return;
        const items = (res.data?.items ?? []) as InstrumentSummary[];
        const filtered = (Array.isArray(items) ? items : []).filter(
          (it) => it?.symbol && !normalizedSymbols.has(String(it.symbol).toUpperCase())
        );
        setSuggestions(filtered);
      } catch {
        if (suggestionsReqId.current !== reqId) return;
        setSuggestions([]);
      } finally {
        if (suggestionsReqId.current === reqId) {
          setSuggestionsLoading(false);
        }
      }
    }, 200);

    return () => {
      window.clearTimeout(handle);
    };
  }, [open, query, normalizedSymbols]);

  // Width is now controlled via CSS classes; constants kept for GlobalHeader layout.

  const signOut = () => {
    logout();
    try {
      sessionStorage.removeItem(HOME_WELCOME_DISMISSED_KEY);
    } catch {
      // Ignore sessionStorage errors
    }
    navigate('/auth/login');
  };

  const currentWidth = open ? drawerWidth : widthClosed;

  const drawerVars = useMemo(
    () => ({
      '--drawer-open': `${drawerWidth}px`,
      '--drawer-closed': `${widthClosed}px`,
    }) as React.CSSProperties,
    [drawerWidth, widthClosed]
  );

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      className={`thor-drawer ${open ? 'open' : 'closed'}`}
      sx={{
        width: currentWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: currentWidth,
          overflow: 'hidden',
          position: 'relative',
          transition: isResizing ? 'none' : 'width 0.2s ease',
        },
      }}
      style={drawerVars}
    >
      {open && (
        <Box
          role="separator"
          aria-orientation="vertical"
          onMouseDown={handleResizeMouseDown}
          sx={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: 8,
            height: '100%',
            cursor: 'col-resize',
            zIndex: 2,
            backgroundColor: isResizing ? 'rgba(255,255,255,0.12)' : 'transparent',
            transition: 'background-color 0.2s ease',
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.12)',
            },
          }}
        />
      )}
      <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: 1 }}>
        <IconButton onClick={onToggle} className="thor-drawer-toggle" aria-label={open ? 'Collapse menu' : 'Expand menu'}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>

      {/* Account Information Section */}
      {open && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" className="thor-account-title" sx={{ mb: 1 }}>
              Account Info
            </Typography>
            <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Option Buying Power</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Net Liq & Day Trades</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$86,081.37</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trading Buying Power</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trades Left</span>
                <Box component="span" sx={{ color: '#ff9800' }}>3</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Cash & Sweep Vehicle</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Available Funds For Trading</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
            </Box>
          </Box>
          <Divider sx={{ mx: 1 }} />
        </>
      )}

      {open && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" className="thor-account-title" sx={{ mb: 1 }}>
              Watchlist
            </Typography>

            <Box className="thor-watchlist-controls">
              <TextField
                size="small"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Add symbol"
                fullWidth
                InputProps={{
                  endAdornment: suggestionsLoading ? <CircularProgress size={16} /> : undefined,
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void addSymbol(query);
                  }
                }}
              />
              <Button
                variant="outlined"
                className="thor-watchlist-add"
                onClick={() => void addSymbol(query)}
                disabled={!query.trim()}
              >
                Add
              </Button>
            </Box>

            {watchlistError && (
              <Box className="thor-watchlist-error">{watchlistError}</Box>
            )}

            {suggestions.length > 0 && (
              <Box className="thor-watchlist-suggestions">
                {suggestions.slice(0, 8).map((s) => (
                  <button
                    type="button"
                    key={s.id}
                    className="thor-watchlist-suggestion"
                    onClick={() => void addSymbol(s.symbol)}
                  >
                    <span>{s.symbol}</span>
                    <span className="thor-watchlist-suggestion-name">{s.name || s.asset_type}</span>
                  </button>
                ))}
              </Box>
            )}

            <Box className="thor-watchlist-items">
              {watchlistLoading ? (
                <Box className="thor-watchlist-muted">Loading…</Box>
              ) : watchlist.length === 0 ? (
                <Box className="thor-watchlist-muted">No symbols yet.</Box>
              ) : (
                watchlist.map((w) => {
                  const sym = (w.instrument?.symbol ?? '').toUpperCase();
                  const data = marketData[sym] || {};
                  return (
                    <WatchlistItemRow
                      key={sym}
                      symbol={sym}
                      data={data}
                      onRemove={(s) => void removeSymbol(s)}
                    />
                  );
                })
              )}
            </Box>
          </Box>
          <Divider sx={{ mx: 1 }} />
        </>
      )}

      <List>
        {navigationItems.map((item) => {
          const selected = !item.external && location.pathname.startsWith(item.path);
          return (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                className="thor-nav-button"
                selected={selected}
                onClick={() => {
                  if (item.external) {
                    window.open(item.path, '_blank', 'noopener,noreferrer');
                    return;
                  }
                  navigate(item.path);
                }}
            >
              <ListItemIcon className="thor-nav-icon">
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} className="thor-nav-text" />
            </ListItemButton>
          </ListItem>
        );})}
      </List>

      {/* Sign out at bottom */}
      <Box sx={{ flexGrow: 1 }} />
      <List>
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            onClick={signOut}
            className="thor-nav-button"
          >
            <ListItemIcon className="thor-nav-icon">
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Sign out" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default CollapsibleDrawer;
