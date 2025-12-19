# WebSocket Integration Guide

## Overview

The WebSocket manager provides real-time communication between the Thor backend and frontend. Messages are type-safe and fully integrated with React hooks.

## Architecture

```
Backend Heartbeat → WebSocket Server → Frontend WebSocket Manager → React Hooks → UI Components
```

## Message Types from Backend

The backend sends these message types:

### Market Status Update
```typescript
{
  type: 'market_status',
  market_id: 1,
  country: 'USA',
  status: 'OPEN' | 'CLOSED' | 'PREOPEN' | 'PRECLOSE',
  current_state: 'OPEN',
  seconds_to_next_event: 3600,
  timestamp: '2025-12-19T15:30:00Z'
}
```

### Intraday Bar Update
```typescript
{
  type: 'intraday_bar',
  country: 'USA',
  symbol: 'ES',
  timestamp_minute: '2025-12-19T15:30:00Z',
  open_1m: 5050.25,
  high_1m: 5055.75,
  low_1m: 5048.50,
  close_1m: 5052.00,
  volume_1m: 125000
}
```

### Quote Tick Update
```typescript
{
  type: 'quote_tick',
  country: 'USA',
  symbol: 'ES',
  price: 5052.25,
  volume: 5000,
  bid: 5052.00,
  ask: 5052.50,
  spread: 0.50,
  timestamp: '2025-12-19T15:30:15Z'
}
```

### 24-Hour Rolling Metrics
```typescript
{
  type: 'twentyfour_hour',
  country: 'USA',
  symbol: 'ES',
  open_price: 5045.00,
  high_24h: 5060.00,
  low_24h: 5040.00,
  volume_24h: 2500000,
  timestamp: '2025-12-19T15:30:00Z'
}
```

### VWAP Update
```typescript
{
  type: 'vwap',
  country: 'USA',
  symbol: 'ES',
  vwap: 5051.50,
  timestamp: '2025-12-19T15:30:00Z'
}
```

### Heartbeat (Keep-Alive)
```typescript
{
  type: 'heartbeat',
  timestamp: '2025-12-19T15:30:00Z',
  heartbeat_count: 1234
}
```

## Usage Examples

### Example 1: Listen to Market Status Updates

```typescript
import { useWebSocketMessage } from '@/hooks/useWebSocket';
import type { MarketStatusUpdate } from '@/services/websocket';

function MarketStatusDisplay() {
  const [status, setStatus] = useState<MarketStatusUpdate | null>(null);

  useWebSocketMessage('market_status', (msg) => {
    setStatus(msg as MarketStatusUpdate);
  });

  return (
    <div>
      <h2>{status?.country} Market</h2>
      <p>Status: {status?.status}</p>
      <p>State: {status?.current_state}</p>
      <p>Next Event In: {status?.seconds_to_next_event}s</p>
    </div>
  );
}
```

### Example 2: Real-Time Intraday Chart

```typescript
import { useWebSocketMessage } from '@/hooks/useWebSocket';
import type { IntradayBarUpdate } from '@/services/websocket';

function IntradayChart() {
  const [bars, setBars] = useState<IntradayBarUpdate[]>([]);

  useWebSocketMessage('intraday_bar', (msg) => {
    const update = msg as IntradayBarUpdate;
    setBars((prev) => [...prev, update].slice(-100)); // Keep last 100 bars
  });

  return (
    <div>
      <h3>1-Minute Bars</h3>
      <Chart data={bars} />
    </div>
  );
}
```

### Example 3: Connection Status Indicator

```typescript
import { useWebSocketConnection } from '@/hooks/useWebSocket';

function ConnectionStatus() {
  const isConnected = useWebSocketConnection();

  return (
    <div className={isConnected ? 'bg-green-500' : 'bg-red-500'}>
      {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
    </div>
  );
}
```

### Example 4: Send Subscribe Request

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

function SymbolSelector() {
  const { send } = useWebSocket();

  const subscribe = (symbol: string) => {
    send({
      type: 'subscribe',
      symbol: symbol,
      channels: ['quote', 'intraday', 'vwap'],
    });
  };

  return (
    <button onClick={() => subscribe('ES')}>
      Subscribe to ES
    </button>
  );
}
```

### Example 5: Complete Real-Time Dashboard

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';
import type { BackendMessage, MarketStatusUpdate, IntradayBarUpdate, QuoteTickUpdate } from '@/services/websocket';

function RealtimeDashboard() {
  const { connected, send, on } = useWebSocket();
  const [marketStatus, setMarketStatus] = useState<MarketStatusUpdate | null>(null);
  const [latestQuote, setLatestQuote] = useState<QuoteTickUpdate | null>(null);
  const [bars, setBars] = useState<IntradayBarUpdate[]>([]);

  useEffect(() => {
    // Subscribe to market status
    const unsubMarket = on('market_status', (msg) => {
      setMarketStatus(msg as MarketStatusUpdate);
    });

    // Subscribe to quotes
    const unsubQuote = on('quote_tick', (msg) => {
      setLatestQuote(msg as QuoteTickUpdate);
    });

    // Subscribe to intraday bars
    const unsubBars = on('intraday_bar', (msg) => {
      const bar = msg as IntradayBarUpdate;
      setBars((prev) => [...prev, bar].slice(-100));
    });

    return () => {
      unsubMarket();
      unsubQuote();
      unsubBars();
    };
  }, [on]);

  return (
    <div>
      <div>Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}</div>
      
      {marketStatus && (
        <div>
          <h2>{marketStatus.country}</h2>
          <p>{marketStatus.status}</p>
        </div>
      )}

      {latestQuote && (
        <div>
          <h3>{latestQuote.symbol}</h3>
          <p>Price: ${latestQuote.price}</p>
          <p>Bid: ${latestQuote.bid} | Ask: ${latestQuote.ask}</p>
        </div>
      )}

      <div>
        <h3>1m Bars ({bars.length})</h3>
        <Chart data={bars} />
      </div>
    </div>
  );
}
```

## Hook API Reference

### `useWebSocketMessage(messageType, handler, enabled?)`

Subscribe to a specific message type.

**Parameters:**
- `messageType` (string) - The message type to listen for
- `handler` (MessageHandler) - Callback function
- `enabled` (boolean, optional) - Whether to enable the listener (default: true)

**Example:**
```typescript
useWebSocketMessage('market_status', (msg) => {
  console.log('Market update:', msg);
});
```

### `useWebSocketConnection()`

Get current connection status.

**Returns:** `boolean` - true if connected

**Example:**
```typescript
const connected = useWebSocketConnection();
```

### `useWebSocketSend()`

Get function to send messages.

**Returns:** `(message: object) => void`

**Example:**
```typescript
const send = useWebSocketSend();
send({ type: 'subscribe', symbol: 'ES' });
```

### `useWebSocket()`

Complete WebSocket management.

**Returns:**
```typescript
{
  connected: boolean;
  send: (message: object) => void;
  on: (type: string, handler: MessageHandler) => () => void;
  connect: () => void;
  disconnect: () => void;
}
```

**Example:**
```typescript
const { connected, send, on } = useWebSocket();
```

## Configuration

Pass configuration when first accessing the WebSocket manager:

```typescript
import { getWebSocketManager } from '@/services/websocket';

const ws = getWebSocketManager({
  url: 'wss://custom.domain/ws', // Optional: override auto-detected URL
  autoConnect: true, // Default: true
  maxRetries: 10, // Default: 10
  initialRetryDelay: 1000, // Default: 1000ms
  maxRetryDelay: 30000, // Default: 30000ms
});
```

## URL Resolution

WebSocket URL is automatically resolved:

- **Local dev:** `ws://localhost:8000/ws`
- **HTTPS:** Uses `wss://` protocol
- **Cloudflare tunnel:** Uses domain from browser URL

## Error Handling

Errors are logged to console. Components should gracefully handle disconnections:

```typescript
function MyComponent() {
  const connected = useWebSocketConnection();

  if (!connected) {
    return <div>⏳ Connecting...</div>;
  }

  return <RealTimeContent />;
}
```

## Performance Tips

1. **Use specific message types** instead of listening to 'all' messages
2. **Unsubscribe when component unmounts** (hooks do this automatically)
3. **Debounce chart updates** if receiving high-frequency messages
4. **Keep message handlers lightweight** - don't do heavy calculations in handlers

## Testing

For local testing without a backend:

```typescript
import { getWebSocketManager } from '@/services/websocket';

const ws = getWebSocketManager({ autoConnect: false });

// Mock a message
const mockMessage = {
  type: 'market_status',
  market_id: 1,
  country: 'USA',
  status: 'OPEN',
};

// Would be handled by subscribed listeners
```

## Next Steps

1. Backend implements WebSocket server at `/ws` endpoint
2. Backend sends messages in the formats defined above
3. Frontend components subscribe to relevant message types
4. UI updates in real-time as messages arrive

---

**Status:** Ready for backend integration ✅
