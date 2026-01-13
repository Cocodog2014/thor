import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  Box,
  Button,
  CircularProgress,
  IconButton,
  TextField,
  Typography,
} from '@mui/material';
import {
  Close as CloseIcon,
  DragIndicator as DragIndicatorIcon,
} from '@mui/icons-material';
import { useWsConnection, useWsMessage, wsEnabled } from '../../realtime';
import type { WsEnvelope } from '../../realtime/types';
import api from '../../services/api';
import { useSelectedAccount } from '../../context/SelectedAccountContext';

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

interface WatchlistItemRowProps {
  symbol: string;
  dragHandleProps?: DragHandleProps;
  data?: Partial<Record<MetricKey, number>>;
  onRemove?: (symbol: string) => void;
  readOnly?: boolean;
}

const WatchlistItemRow: React.FC<WatchlistItemRowProps> = ({ symbol, dragHandleProps, data, onRemove, readOnly }) => {
  const prevLast = useRef<number | undefined>(undefined);
  const [trend, setTrend] = useState<'up' | 'down' | null>(null);
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);

  const last = data?.last;
  const prevClose = data?.close;
  const netChange = last !== undefined && prevClose !== undefined ? last - prevClose : undefined;
  const netPct = netChange !== undefined && prevClose ? (netChange / prevClose) * 100 : undefined;

  useEffect(() => {
    const current = data?.last;
    if (current !== undefined && prevLast.current !== undefined && current !== prevLast.current) {
      const dir = current > prevLast.current ? 'up' : 'down';
      setTrend(dir);
      setFlash(dir);
      const timer = setTimeout(() => setFlash(null), 650);
      return () => clearTimeout(timer);
    }
    if (current !== undefined) prevLast.current = current;
  }, [data?.last]);

  const baseColor = trend === 'up' ? '#00e676' : trend === 'down' ? '#ff1744' : 'inherit';
  const priceColor = flash === 'up' ? '#69f0ae' : flash === 'down' ? '#ff5252' : baseColor;
  const netColor = netChange === undefined ? 'inherit' : netChange > 0 ? '#00e676' : netChange < 0 ? '#ff1744' : 'inherit';
  const flashBg =
    flash === 'up'
      ? 'rgba(0, 230, 118, 0.18)'
      : flash === 'down'
        ? 'rgba(255, 23, 68, 0.18)'
        : 'transparent';
  const dirGlyph = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '';

  const quoteLabelSx = {
    fontSize: '0.52rem',
    color: 'text.secondary',
    textAlign: 'center' as const,
    lineHeight: 1.1,
    letterSpacing: '0.06em',
    width: '100%',
  };

  const quoteValueSx = {
    fontSize: '0.66rem',
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
            sx={{ cursor: readOnly ? 'default' : 'grab', color: 'text.secondary' }}
            aria-label="Drag to reorder"
            disabled={Boolean(readOnly)}
            {...(!readOnly ? (dragHandleProps?.attributes ?? {}) : {})}
            {...(!readOnly ? (dragHandleProps?.listeners ?? {}) : {})}
          >
            <DragIndicatorIcon fontSize="inherit" />
          </IconButton>
          <Typography
            variant="body2"
            sx={{
              fontSize: '0.7rem',
              fontWeight: 'bold',
              color: '#1976d2',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {symbol}
          </Typography>
        </Box>
        {onRemove && !readOnly ? (
          <IconButton size="small" onClick={() => onRemove(symbol)} aria-label={`Remove ${symbol}`}>
            <CloseIcon fontSize="inherit" />
          </IconButton>
        ) : (
          <Box sx={{ width: 28 }} />
        )}
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, minmax(0, 1fr))',
          columnGap: 2,
          rowGap: 0.5,
          alignItems: 'start',
        }}
      >
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>LAST</Typography>
          <Typography
            noWrap
            sx={{
              ...quoteValueSx,
              fontWeight: 800,
              fontSize: '0.74rem',
              color: priceColor,
              transition: 'color 0.25s, background-color 0.25s',
              backgroundColor: flashBg,
              borderRadius: 0.75,
              pr: 0.5,
            }}
          >
            <Box component="span" sx={{ display: 'inline-block', width: '0.9em', color: priceColor }}>
              {dirGlyph}
            </Box>
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
        <Box sx={metricCellSx}>
          <Typography sx={quoteLabelSx}>NET</Typography>
          <Typography
            noWrap
            sx={{
              ...quoteValueSx,
              color: netColor,
              fontWeight: 700,
            }}
          >
            {netChange === undefined ? '-' : `${netChange >= 0 ? '+' : ''}${netChange.toFixed(2)}`}
            {netPct === undefined ? '' : ` (${netPct >= 0 ? '+' : ''}${netPct.toFixed(2)}%)`}
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

export interface WatchlistProps {
  open: boolean;
  onLastTickAtChange?: (d: Date) => void;
}

const Watchlist: React.FC<WatchlistProps> = ({ open, onLastTickAtChange }) => {
  const dndSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const wsIsEnabled = wsEnabled();
  const wsConnected = useWsConnection(true);

  const { accountId } = useSelectedAccount();

  const [userWatchlist, setUserWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [marketData, setMarketData] = useState<MarketDataMap>({});
  const [query, setQuery] = useState('');
  const [lastTickAt, setLastTickAt] = useState<Date | null>(null);

  const derivedMode = useMemo<'paper' | 'live' | null>(() => {
    if (!accountId) return null;
    const s = String(accountId).trim().toUpperCase();
    if (!s) return null;
    // Current backend convention: paper broker_account_id values are PAPER-*.
    return s.startsWith('PAPER') ? 'paper' : 'live';
  }, [accountId]);


  const setTickNow = useCallback(() => {
    const d = new Date();
    setLastTickAt(d);
    onLastTickAtChange?.(d);
  }, [onLastTickAtChange]);

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

  const applyMarketQuotesBatch = useCallback((quotes: SnapshotQuote[]) => {
    if (!quotes.length) return;

    setMarketData((prev) => {
      let changedAny = false;
      const nextAll: MarketDataMap = { ...prev };

      for (const q of quotes) {
        const symbol = normalizeWsSymbol(q?.symbol);
        if (!symbol) continue;

        const current = prev[symbol] || {};
        const next = { ...current };
        let changed = false;

        const patch: Partial<Record<MetricKey, unknown>> = {
          bid: (q as unknown as { bid?: unknown }).bid,
          ask: (q as unknown as { ask?: unknown }).ask,
          last: (q as unknown as { last?: unknown; price?: unknown }).last
            ?? (q as unknown as { price?: unknown }).price,
          volume: (q as unknown as { volume?: unknown }).volume,
          open: (q as unknown as { open?: unknown; open_price?: unknown }).open
            ?? (q as unknown as { open_price?: unknown }).open_price,
          high: (q as unknown as { high?: unknown; high_price?: unknown }).high
            ?? (q as unknown as { high_price?: unknown }).high_price,
          low: (q as unknown as { low?: unknown; low_price?: unknown }).low
            ?? (q as unknown as { low_price?: unknown }).low_price,
          close: (q as unknown as { close?: unknown; close_price?: unknown }).close
            ?? (q as unknown as { close_price?: unknown }).close_price,
        };

        (Object.entries(patch) as Array<[MetricKey, unknown]>).forEach(([key, raw]) => {
          const val = toNumeric(raw);
          if (val !== undefined && next[key] !== val) {
            next[key] = val;
            changed = true;
          }
        });

        if (changed) {
          nextAll[symbol] = next;
          changedAny = true;
        }
      }

      return changedAny ? nextAll : prev;
    });
  }, []);

  const loadSnapshotForSymbols = useCallback(async (symbols: string[]) => {
    const normalized = symbols
      .map((s) => normalizeWsSymbol(s))
      .filter(Boolean);

    if (normalized.length === 0) return;

    try {
      const res = await api.get('/feed/quotes/snapshot/', {
        params: { symbols: normalized.join(',') },
      });

      const data = res.data as { quotes?: unknown };
      const quotesRaw = data?.quotes;
      const quotes = Array.isArray(quotesRaw) ? (quotesRaw as SnapshotQuote[]) : [];
      applyMarketQuotesBatch(quotes);
    } catch (err) {
      console.error('Watchlist snapshot fetch failed', err);
    }
  }, [applyMarketQuotesBatch]);

  const canWrite = derivedMode !== null;

  // WS events
  useWsMessage('quote_tick', (msg: WsEnvelope<QuoteTickPayload>) => {
    setTickNow();
    applyMarketPatch(msg.data?.symbol, {
      bid: msg.data?.bid,
      ask: msg.data?.ask,
      last: msg.data?.last ?? msg.data?.price,
      volume: msg.data?.volume,
    });
  });

  useWsMessage('market_data', (msg: WsEnvelope<{ quotes?: unknown }>) => {
    const quotesRaw = msg.data?.quotes;
    if (!Array.isArray(quotesRaw)) return;
    setTickNow();
    applyMarketQuotesBatch(quotesRaw as SnapshotQuote[]);
  });

  useWsMessage('market_24h', (msg: WsEnvelope<Market24hPayload>) => {
    setTickNow();
    applyMarketPatch(msg.data?.symbol, {
      open: msg.data?.open ?? msg.data?.open_price,
      high: msg.data?.high ?? msg.data?.high_price,
      low: msg.data?.low ?? msg.data?.low_price,
      close: msg.data?.close ?? msg.data?.close_price,
      volume: msg.data?.volume,
    });
  });

  // Actions
  const loadUserWatchlist = useCallback(async (nextMode: 'paper' | 'live' | null) => {
    const res = await api.get('/instruments/watchlist/', {
      params: nextMode ? { mode: nextMode } : {},
    });
    const items = Array.isArray(res.data?.items) ? (res.data.items as WatchlistItem[]) : [];
    setUserWatchlist(items);
    return items;
  }, []);

  const loadWatchlists = useCallback(async () => {
    setWatchlistLoading(true);
    try {
      const userItems = await loadUserWatchlist(derivedMode);

      const symbols = [...userItems]
        .map((w) => w.instrument?.symbol)
        .filter((s): s is string => typeof s === 'string' && Boolean(s.trim()))
        .map((s) => s.toUpperCase());

      await loadSnapshotForSymbols(symbols);
    } catch (err) {
      console.error(err);
    } finally {
      setWatchlistLoading(false);
    }
  }, [derivedMode, loadSnapshotForSymbols, loadUserWatchlist]);

  const persistWatchlistOrder = useCallback(async (items: WatchlistItem[]) => {
    if (!derivedMode) return;
    try {
      await api.put(
        '/instruments/watchlist/',
        {
          items: items.map((item, i) => ({
            symbol: item.instrument?.symbol ?? '',
            order: i,
          })),
        },
        { params: { mode: derivedMode } }
      );
    } catch (err) {
      console.error('Failed to persist watchlist order', err);
    }
  }, [derivedMode]);

  const addSymbol = useCallback(async (symbolRaw: string) => {
    if (!symbolRaw) return;
    if (!derivedMode) return;

    const sym = symbolRaw.toUpperCase();
    const next = [...userWatchlist, { instrument: { symbol: sym } }];
    setUserWatchlist(next);
    setQuery('');

    loadSnapshotForSymbols([sym]);

    try {
      await api.put(
        '/instruments/watchlist/',
        { items: next.map((item, i) => ({ symbol: item.instrument?.symbol ?? '', order: i })) },
        { params: { mode: derivedMode } }
      );
      await loadWatchlists();
    } catch (e) {
      console.error(e);
    }
  }, [derivedMode, loadSnapshotForSymbols, loadWatchlists, userWatchlist]);

  const removeSymbol = useCallback(async (symbol: string) => {
    const next = userWatchlist.filter((w) => w.instrument?.symbol?.toUpperCase() !== symbol);
    setUserWatchlist(next);
    await persistWatchlistOrder(next);
  }, [persistWatchlistOrder, userWatchlist]);

  useEffect(() => {
    if (!open) return;
    void loadWatchlists();
  }, [open, loadWatchlists]);

  useEffect(() => {
    if (!open) return;
    void loadUserWatchlist(derivedMode);
  }, [open, derivedMode, loadUserWatchlist]);

  // Snapshot fallback when WS is disabled/disconnected/stale.
  useEffect(() => {
    if (!open) return;

    const symbols = [...userWatchlist]
      .map((w) => w.instrument?.symbol)
      .filter((s): s is string => typeof s === 'string' && Boolean(s.trim()))
      .map((s) => s.toUpperCase());

    if (symbols.length === 0) return;

    const isWsFresh = () => {
      if (!(wsIsEnabled && wsConnected)) return false;
      if (!lastTickAt) return false;
      return Date.now() - lastTickAt.getTime() < 8000;
    };

    const interval = window.setInterval(() => {
      if (isWsFresh()) return;
      void loadSnapshotForSymbols(symbols);
    }, 5000);

    return () => window.clearInterval(interval);
  }, [open, wsConnected, wsIsEnabled, lastTickAt, userWatchlist, loadSnapshotForSymbols]);

  const watchlistIds = useMemo(
    () => userWatchlist.map((item) => String(item.instrument?.symbol ?? '')),
    [userWatchlist]
  );

  const renderRows = useMemo(() => {
    return userWatchlist.map((w) => {
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
    });
  }, [marketData, removeSymbol, userWatchlist]);

  return (
    <>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>Watchlist</Typography>
      <Box className="thor-watchlist-controls" sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Add symbol"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void addSymbol(query); }}
          disabled={!canWrite}
        />
        <Button
          className="thor-watchlist-add"
          variant="outlined"
          size="small"
          onClick={() => void addSymbol(query)}
          disabled={!canWrite || !query.trim()}
        >
          Add
        </Button>
      </Box>

      <Box sx={{ flex: '0 0 50%', maxHeight: '50%', minHeight: 0, overflowY: 'auto', pb: 1 }}>
        {watchlistLoading ? (
          <CircularProgress size={20} />
        ) : (
          <>
            <Typography variant="caption" sx={{ display: 'block', px: 1.5, pt: 1, pb: 0.5, color: 'text.secondary' }}>
              My watchlist
            </Typography>

            <DndContext
              sensors={dndSensors}
              collisionDetection={closestCenter}
              onDragEnd={(event: DragEndEvent) => {
                const { active, over } = event;
                if (!over || active.id === over.id) return;

                setUserWatchlist((prev) => {
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
                items={watchlistIds}
                strategy={verticalListSortingStrategy}
              >
                {renderRows}
              </SortableContext>
            </DndContext>
          </>
        )}
      </Box>
    </>
  );
};

export default Watchlist;
