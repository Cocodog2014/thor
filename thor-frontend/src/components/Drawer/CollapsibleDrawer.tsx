import React, { useEffect, useMemo, useRef, useState } from 'react';
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

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  // widthOpen = DEFAULT_WIDTH_OPEN,
  // widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);

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

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      className={`thor-drawer ${open ? 'open' : 'closed'}`}
    >
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
                placeholder="Add symbol (e.g. VFF)"
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
                  return (
                    <Box key={sym} className="thor-watchlist-item">
                      <span className="thor-watchlist-symbol">{sym}</span>
                      <IconButton
                        size="small"
                        onClick={() => void removeSymbol(sym)}
                        aria-label={`Remove ${sym}`}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    </Box>
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
