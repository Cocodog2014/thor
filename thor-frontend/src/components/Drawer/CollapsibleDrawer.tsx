import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 1. Remove the 'react-use-websocket' import
// import useWebSocket from 'react-use-websocket'; 
import { useWsConnection, useWsMessage, wsEnabled } from '../../realtime'; // <--- Use this instead
import type { WsEnvelope } from '../../realtime/types';
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
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
  Button,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon,
  Close as CloseIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
  DragIndicator as DragIndicatorIcon,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';

// --- Constants & Helpers ---
export const DEFAULT_WIDTH_OPEN = 500;
export const DEFAULT_WIDTH_CLOSED = 72;
const MIN_DRAWER_WIDTH = 100;
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

type SortableHookReturn = ReturnType<typeof useSortable>;
type DragHandleProps = {
  attributes: SortableHookReturn['attributes'];
  listeners?: SortableHookReturn['listeners'];
};

type WatchlistItem = {
  instrument?: {
    symbol?: string;
  };
};

type QuoteTickPayload = {
  symbol?: unknown;
  bid?: unknown;
  ask?: unknown;
  last?: unknown;
  price?: unknown;
  volume?: unknown;
};

type Market24hPayload = {
  symbol?: unknown;
  open?: unknown;
  open_price?: unknown;
  high?: unknown;
  high_price?: unknown;
  low?: unknown;
  low_price?: unknown;
  close?: unknown;
  close_price?: unknown;
  volume?: unknown;
};

type SnapshotQuote = {
  symbol?: unknown;
  bid?: unknown;
  ask?: unknown;
  last?: unknown;
  price?: unknown;
  volume?: unknown;
  open?: unknown;
  open_price?: unknown;
  high?: unknown;
  high_price?: unknown;
  low?: unknown;
  low_price?: unknown;
  close?: unknown;
  close_price?: unknown;
};

interface WatchlistItemRowProps {
  symbol: string;
  dragHandleProps?: DragHandleProps;
  data?: Partial<Record<MetricKey, number>>;
  onRemove: (symbol: string) => void;
}

const WatchlistItemRow: React.FC<WatchlistItemRowProps> = ({ symbol, dragHandleProps, data, onRemove }) => {
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

  const quoteLabelSx = {
    fontSize: '0.65rem',
    color: 'text.secondary',
    textAlign: 'center' as const,
    lineHeight: 1.1,
    letterSpacing: '0.06em',
    width: '100%',
  };

  const quoteValueSx = {
    fontSize: '0.82rem',
    fontVariantNumeric: 'tabular-nums',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    textAlign: 'left' as const,
    lineHeight: 1.2,
    width: '100%',
    pl: 0.5,
  };

  const metricCellSx = {
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'stretch',
    gap: 0.25,
  };

  return (
    <Box className="thor-watchlist-item" sx={{ p: 1.5, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
          <IconButton
            size="small"
            sx={{ cursor: 'grab', color: 'text.secondary' }}
            aria-label="Drag to reorder"
            {...(dragHandleProps?.attributes ?? {})}
            {...(dragHandleProps?.listeners ?? {})}
          >
            <DragIndicatorIcon fontSize="inherit" />
          </IconButton>
          <Typography
            variant="body2"
            sx={{ fontWeight: 'bold', color: '#1976d2', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {symbol}
          </Typography>
        </Box>
        <IconButton size="small" onClick={() => onRemove(symbol)} aria-label={`Remove ${symbol}`}>
          <CloseIcon fontSize="inherit" />
        </IconButton>
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          columnGap: 2,
          rowGap: 0.5,
          alignItems: 'start',
        }}
      >
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>LAST</Typography>
          <Typography
            noWrap
            sx={{ ...quoteValueSx, fontWeight: 700, color: priceColor, transition: 'color 0.3s' }}
          >
            {formatPrice(data?.last)}
          </Typography>
        </Box>
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>BID</Typography>
          <Typography noWrap sx={quoteValueSx}>
            {formatPrice(data?.bid)}
          </Typography>
        </Box>
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>ASK</Typography>
          <Typography noWrap sx={quoteValueSx}>
            {formatPrice(data?.ask)}
          </Typography>
        </Box>
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>VOL</Typography>
          <Typography noWrap sx={quoteValueSx}>
            {formatVolume(data?.volume)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

type SortableWatchlistRowProps = {
  id: string;
  symbol: string;
  data?: Partial<Record<MetricKey, number>>;
  onRemove: (symbol: string) => void;
};

const SortableWatchlistRow: React.FC<SortableWatchlistRowProps> = ({ id, symbol, data, onRemove }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.85 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <WatchlistItemRow
        symbol={symbol}
        data={data}
        onRemove={onRemove}
        dragHandleProps={{ attributes, listeners }}
      />
    </div>
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

  const dndSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const wsIsEnabled = wsEnabled();
  const wsConnected = useWsConnection(true);
  const [lastTickAt, setLastTickAt] = useState<Date | null>(null);

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

  const loadSnapshotForSymbols = useCallback(async (symbols: string[]) => {
    const normalized = symbols
      .map((s) => normalizeWsSymbol(s))
      .filter(Boolean);

    if (normalized.length === 0) return;

    try {
      // NOTE: api baseURL already includes `/api`, so this hits:
      // GET /api/feed/quotes/snapshot/?symbols=AAPL,MSFT,...
      const res = await api.get('/feed/quotes/snapshot/', {
        params: { symbols: normalized.join(',') },
      });

      const data = res.data as { quotes?: unknown };
      const quotesRaw = data?.quotes;
      const quotes = Array.isArray(quotesRaw) ? (quotesRaw as SnapshotQuote[]) : [];
      quotes.forEach((q) => {
        applyMarketPatch(q?.symbol, {
          bid: q?.bid,
          ask: q?.ask,
          last: q?.last ?? q?.price,
          volume: q?.volume,
          open: q?.open ?? q?.open_price,
          high: q?.high ?? q?.high_price,
          low: q?.low ?? q?.low_price,
          close: q?.close ?? q?.close_price,
        });
      });
    } catch (err) {
      console.error('Watchlist snapshot fetch failed', err);
    }
  }, [applyMarketPatch]);

  // Use the shared global socket connection
  useWsMessage('quote_tick', (msg: WsEnvelope<QuoteTickPayload>) => {
    setLastTickAt(new Date());
    applyMarketPatch(msg.data?.symbol, {
      bid: msg.data?.bid,
      ask: msg.data?.ask,
      last: msg.data?.last ?? msg.data?.price,
      volume: msg.data?.volume,
    });
  });

  useWsMessage('market.24h', (msg: WsEnvelope<Market24hPayload>) => {
    setLastTickAt(new Date());
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
  const loadWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    try {
      const res = await api.get('/instruments/watchlist/');
      const items = Array.isArray(res.data?.items) ? (res.data.items as WatchlistItem[]) : [];
      setWatchlist(items);

      // Seed from Redis snapshot (fed by Schwab streamer), then WS ticks keep it live.
      const symbols = items
        .map((w) => w.instrument?.symbol)
        .filter((s): s is string => typeof s === 'string' && Boolean(s.trim()))
        .map((s) => s.toUpperCase());
      await loadSnapshotForSymbols(symbols);
    } catch (err) {
      console.error(err);
    } finally {
      setWatchlistLoading(false);
    }
  }, [loadSnapshotForSymbols]);

  const persistWatchlistOrder = useCallback(async (items: WatchlistItem[]) => {
    try {
      await api.put('/instruments/watchlist/', {
        items: items.map((item, i) => ({
          symbol: item.instrument?.symbol ?? '',
          order: i,
        })),
      });
    } catch (err) {
      console.error('Failed to persist watchlist order', err);
    }
  }, []);

  const addSymbol = async (symbolRaw: string) => {
    if (!symbolRaw) return;
    // Optimistic UI update
    const sym = symbolRaw.toUpperCase();
    const next = [...watchlist, { instrument: { symbol: sym } }];
    setWatchlist(next);
    setQuery('');
    // Best-effort seed for the new symbol.
    loadSnapshotForSymbols([sym]);
    try {
      await api.put('/instruments/watchlist/', { items: next.map((item, i) => ({ symbol: item.instrument?.symbol ?? '', order: i })) });
      loadWatchlist(); 
    } catch (e) { console.error(e); }
  };

  const removeSymbol = async (symbol: string) => {
    const next = watchlist.filter(w => w.instrument?.symbol?.toUpperCase() !== symbol);
    setWatchlist(next);
    await persistWatchlistOrder(next);
  };

  useEffect(() => {
    if (open) loadWatchlist();
  }, [open, loadWatchlist]);

  const signOut = () => { logout(); sessionStorage.removeItem(HOME_WELCOME_DISMISSED_KEY); navigate('/auth/login'); };
  const currentWidth = open ? drawerWidth : widthClosed;

  const wsStatusLabel = wsIsEnabled ? (wsConnected ? 'WS: Connected' : 'WS: Disconnected') : 'WS: Disabled';
  const wsStatusColor = !wsIsEnabled ? 'text.secondary' : wsConnected ? '#4caf50' : '#f44336';
  const wsLastTickLabel = lastTickAt ? ` · last tick ${lastTickAt.toLocaleTimeString('en-US')}` : '';

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
      <Toolbar sx={{ justifyContent: open ? 'space-between' : 'center', px: 1 }}>
        {open && (
          <Typography
            variant="caption"
            sx={{
              color: wsStatusColor,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '75%',
            }}
            title={`${wsStatusLabel}${wsLastTickLabel}`}
          >
            {wsStatusLabel}{wsLastTickLabel}
          </Typography>
        )}

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
            {watchlistLoading ? (
              <CircularProgress size={20} />
            ) : (
              <DndContext
                sensors={dndSensors}
                collisionDetection={closestCenter}
                onDragEnd={(event: DragEndEvent) => {
                  const { active, over } = event;
                  if (!over || active.id === over.id) return;

                  setWatchlist((prev) => {
                    const ids = prev.map((item) => String(item.instrument?.symbol ?? ''));
                    const oldIndex = ids.indexOf(String(active.id));
                    const newIndex = ids.indexOf(String(over.id));
                    if (oldIndex < 0 || newIndex < 0) return prev;

                    const next = arrayMove(prev, oldIndex, newIndex);
                    void persistWatchlistOrder(next);
                    return next;
                  });
                }}
              >
                <SortableContext
                  items={watchlist.map((item) => String(item.instrument?.symbol ?? ''))}
                  strategy={verticalListSortingStrategy}
                >
                  {watchlist.map((w) => {
                    const displaySymbol = (w.instrument?.symbol || '').toUpperCase();
                    const id = String(w.instrument?.symbol ?? '');
                    const dataKey = normalizeWsSymbol(displaySymbol);
                    return (
                      <SortableWatchlistRow
                        key={id}
                        id={id}
                        symbol={displaySymbol}
                        data={dataKey ? marketData[dataKey] : undefined}
                        onRemove={removeSymbol}
                      />
                    );
                  })}
                </SortableContext>
              </DndContext>
            )}
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