/**
 * Example Component: Real-Time Market Dashboard
 *
 * Shows how to use WebSocket hooks in a real React component
 */

import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import type {
  MarketStatusUpdate,
  IntradayBarUpdate,
  QuoteTickUpdate,
  TwentyFourHourUpdate,
  VwapUpdate,
} from '@/services/websocket';

interface MarketData {
  marketStatus: MarketStatusUpdate | null;
  latestQuote: QuoteTickUpdate | null;
  latestBar: IntradayBarUpdate | null;
  latest24h: TwentyFourHourUpdate | null;
  vwap: VwapUpdate | null;
  barCount: number;
  lastUpdate: string;
}

/**
 * Example: Real-Time Market Dashboard Component
 *
 * Usage:
 * <RealtimeMarketDashboard country="USA" symbol="ES" />
 */
export function RealtimeMarketDashboard({
  country = 'USA',
  symbol = 'ES',
}: {
  country?: string;
  symbol?: string;
}) {
  const { connected, send, on } = useWebSocket();
  const [data, setData] = useState<MarketData>({
    marketStatus: null,
    latestQuote: null,
    latestBar: null,
    latest24h: null,
    vwap: null,
    barCount: 0,
    lastUpdate: 'Never',
  });

  // Subscribe to WebSocket messages
  useEffect(() => {
    const unsubscribers: Array<() => void> = [];

    // Subscribe to market status
    unsubscribers.push(
      on('market_status', (msg) => {
        const status = msg as MarketStatusUpdate;
        if (status.country === country) {
          setData((prev) => ({
            ...prev,
            marketStatus: status,
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      })
    );

    // Subscribe to quote updates
    unsubscribers.push(
      on('quote_tick', (msg) => {
        const quote = msg as QuoteTickUpdate;
        if (quote.country === country && quote.symbol === symbol) {
          setData((prev) => ({
            ...prev,
            latestQuote: quote,
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      })
    );

    // Subscribe to intraday bars
    unsubscribers.push(
      on('intraday_bar', (msg) => {
        const bar = msg as IntradayBarUpdate;
        if (bar.country === country && bar.symbol === symbol) {
          setData((prev) => ({
            ...prev,
            latestBar: bar,
            barCount: prev.barCount + 1,
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      })
    );

    // Subscribe to 24h metrics
    unsubscribers.push(
      on('twentyfour_hour', (msg) => {
        const m24h = msg as TwentyFourHourUpdate;
        if (m24h.country === country && m24h.symbol === symbol) {
          setData((prev) => ({
            ...prev,
            latest24h: m24h,
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      })
    );

    // Subscribe to VWAP
    unsubscribers.push(
      on('vwap', (msg) => {
        const vwap = msg as VwapUpdate;
        if (vwap.country === country && vwap.symbol === symbol) {
          setData((prev) => ({
            ...prev,
            vwap: vwap,
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      })
    );

    // Cleanup: Unsubscribe when component unmounts
    return () => {
      unsubscribers.forEach((unsub) => unsub());
    };
  }, [on, country, symbol]);

  // Example: Send a subscription request to backend (if backend requires it)
  useEffect(() => {
    if (connected) {
      send({
        type: 'subscribe',
        country,
        symbol,
        channels: ['market_status', 'quote', 'intraday', 'vwap'],
      });
    }
  }, [connected, send, country, symbol]);

  // Helper function to format price
  const formatPrice = (price: number | undefined) => {
    if (price === undefined) return '-';
    return price.toFixed(2);
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center border-b pb-4">
        <h1 className="text-2xl font-bold">
          {country} - {symbol}
        </h1>
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              connected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm">
            {connected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          <span className="text-xs text-gray-500 ml-4">
            Last update: {data.lastUpdate}
          </span>
        </div>
      </div>

      {/* Market Status */}
      {data.marketStatus && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Status</div>
            <div className="text-lg font-semibold">{data.marketStatus.status}</div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">State</div>
            <div className="text-lg font-semibold">{data.marketStatus.current_state}</div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Next Event In</div>
            <div className="text-lg font-semibold">
              {Math.floor(data.marketStatus.seconds_to_next_event / 60)}m
            </div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Bars Received</div>
            <div className="text-lg font-semibold">{data.barCount}</div>
          </div>
        </div>
      )}

      {/* Quote Data */}
      {data.latestQuote && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-4 rounded">
            <div className="text-xs text-gray-600">Price</div>
            <div className="text-3xl font-bold">
              ${formatPrice(data.latestQuote.price)}
            </div>
            <div className="text-xs text-gray-600 mt-2">
              Volume: {(data.latestQuote.volume / 1000).toFixed(1)}k
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-green-50 p-4 rounded">
              <div className="text-xs text-gray-600">Bid</div>
              <div className="text-xl font-semibold">
                ${formatPrice(data.latestQuote.bid)}
              </div>
            </div>
            <div className="bg-red-50 p-4 rounded">
              <div className="text-xs text-gray-600">Ask</div>
              <div className="text-xl font-semibold">
                ${formatPrice(data.latestQuote.ask)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 1-Minute Bar */}
      {data.latestBar && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Open (1m)</div>
            <div className="text-lg font-semibold">${formatPrice(data.latestBar.open_1m)}</div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">High (1m)</div>
            <div className="text-lg font-semibold">${formatPrice(data.latestBar.high_1m)}</div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Low (1m)</div>
            <div className="text-lg font-semibold">${formatPrice(data.latestBar.low_1m)}</div>
          </div>
          <div className="bg-gray-100 p-3 rounded">
            <div className="text-xs text-gray-600">Close (1m)</div>
            <div className="text-lg font-semibold">${formatPrice(data.latestBar.close_1m)}</div>
          </div>
        </div>
      )}

      {/* 24h Metrics */}
      {data.latest24h && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-purple-50 p-3 rounded">
            <div className="text-xs text-gray-600">24h Open</div>
            <div className="font-semibold">${formatPrice(data.latest24h.open_price)}</div>
          </div>
          <div className="bg-purple-50 p-3 rounded">
            <div className="text-xs text-gray-600">24h High</div>
            <div className="font-semibold">${formatPrice(data.latest24h.high_24h)}</div>
          </div>
          <div className="bg-purple-50 p-3 rounded">
            <div className="text-xs text-gray-600">24h Low</div>
            <div className="font-semibold">${formatPrice(data.latest24h.low_24h)}</div>
          </div>
        </div>
      )}

      {/* VWAP */}
      {data.vwap && (
        <div className="bg-indigo-50 p-4 rounded">
          <div className="text-xs text-gray-600">VWAP</div>
          <div className="text-2xl font-bold">${formatPrice(data.vwap.vwap)}</div>
        </div>
      )}

      {/* No Data State */}
      {!data.marketStatus &&
        !data.latestQuote &&
        !data.latestBar &&
        !data.latest24h &&
        !data.vwap && (
          <div className="text-center py-8 text-gray-500">
            {connected ? (
              <p>⏳ Waiting for real-time data...</p>
            ) : (
              <p>🔌 Waiting for WebSocket connection...</p>
            )}
          </div>
        )}
    </div>
  );
}

export default RealtimeMarketDashboard;
