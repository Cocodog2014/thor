/**
 * WebSocket Manager for Thor Real-Time Backend Communication
 *
 * Handles:
 * - Connection lifecycle (connect, disconnect, reconnect)
 * - Message routing to handlers
 * - Type-safe message interfaces
 * - Automatic reconnection with exponential backoff
 * - Event subscription/unsubscription
 */

import { ThorEvent } from '../realtime/events';

// ============================================================================
// Backend Message Types
// ============================================================================

/**
 * Market status update from heartbeat
 */
export interface MarketStatusUpdate {
  type: 'market_status';
  market_id: number;
  country: string;
  status: 'OPEN' | 'CLOSED' | 'PREOPEN' | 'PRECLOSE';
  current_state: string;
  seconds_to_next_event: number;
  timestamp: string; // ISO 8601
}

/**
 * Intraday bar snapshot (1-minute OHLCV)
 */
export interface IntradayBarUpdate {
  type: 'intraday_bar';
  country: string;
  symbol: string;
  timestamp_minute: string; // ISO 8601
  open_1m: number;
  high_1m: number;
  low_1m: number;
  close_1m: number;
  volume_1m: number;
}

/**
 * Real-time quote tick
 */
export interface QuoteTickUpdate {
  type: 'quote_tick';
  country: string;
  symbol: string;
  price: number;
  volume: number;
  bid: number;
  ask: number;
  spread: number;
  timestamp: string; // ISO 8601
}

/**
 * 24-hour rolling metrics
 */
export interface TwentyFourHourUpdate {
  type: 'twentyfour_hour';
  country: string;
  symbol: string;
  open_price: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  timestamp: string;
}

/**
 * VWAP snapshot
 */
export interface VwapUpdate {
  type: 'vwap';
  country: string;
  symbol: string;
  vwap: number;
  timestamp: string;
}

/**
 * Heartbeat message (keep-alive)
 */
export interface HeartbeatMessage {
  type: 'heartbeat';
  timestamp: string;
  heartbeat_count: number;
}

/**
 * Error message
 */
export interface ErrorMessage {
  type: 'error';
  message: string;
  error_code?: string;
  timestamp: string;
}

/**
 * Union type of all possible backend messages
 */
export type BackendMessage =
  | MarketStatusUpdate
  | IntradayBarUpdate
  | QuoteTickUpdate
  | TwentyFourHourUpdate
  | VwapUpdate
  | HeartbeatMessage
  | ErrorMessage
  | ThorEvent; // Legacy events

// ============================================================================
// Connection Management Types
// ============================================================================

export type MessageHandler = (message: BackendMessage) => void;
export type ConnectionCallback = (connected: boolean) => void;

export interface WebSocketConfig {
  url?: string;
  autoConnect?: boolean;
  maxRetries?: number;
  initialRetryDelay?: number; // ms
  maxRetryDelay?: number; // ms
}

// ============================================================================
// WebSocket Manager
// ============================================================================

class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private connectionHandlers: Set<ConnectionCallback> = new Set();
  private connected = false;
  private retryCount = 0;
  private maxRetries = 10;
  private retryDelay = 1000; // Start at 1s
  private maxRetryDelay = 30000; // Cap at 30s
  private retryTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimeout = 5000; // 5s without heartbeat = dead
  private messageQueue: string[] = [];

  constructor(config: WebSocketConfig = {}) {
    this.url = config.url || this.resolveWebSocketUrl();
    this.maxRetries = config.maxRetries ?? 10;
    this.retryDelay = config.initialRetryDelay ?? 1000;
    this.maxRetryDelay = config.maxRetryDelay ?? 30000;

    if (config.autoConnect !== false) {
      this.connect();
    }
  }

  /**
   * Resolve WebSocket URL similar to how API URL is resolved
   */
  private resolveWebSocketUrl(): string {
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';

    if (typeof window !== 'undefined') {
      const host = window.location.hostname;
      const port = window.location.port;

      // Local dev
      if (host === 'localhost' || host === '127.0.0.1') {
        return `${protocol}://localhost:8000/ws`;
      }

      // Remote (Cloudflare tunnel, etc.)
      const baseUrl = `${host}${port ? `:${port}` : ''}`;
      return `${protocol}://${baseUrl}/ws`;
    }

    return `${protocol}://localhost:8000/ws`;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws && this.connected) {
      console.log('[WS] Already connected');
      return;
    }

    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
      this.retryTimeoutId = null;
    }

    console.log(`[WS] Connecting to ${this.url}...`);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => this.onOpen();
      this.ws.onmessage = (event) => this.onMessage(event);
      this.ws.onerror = (event) => this.onError(event);
      this.ws.onclose = () => this.onClose();
    } catch (error) {
      console.error('[WS] Connection error:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
      this.retryTimeoutId = null;
    }
    if (this.heartbeatTimeoutId) {
      clearTimeout(this.heartbeatTimeoutId);
      this.heartbeatTimeoutId = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.connected = false;
    this.retryCount = 0;
    console.log('[WS] Disconnected');
  }

  /**
   * Send a message to the server
   */
  send(message: object): void {
    const payload = JSON.stringify(message);

    if (this.connected && this.ws) {
      try {
        this.ws.send(payload);
      } catch (error) {
        console.error('[WS] Send error:', error);
        this.messageQueue.push(payload);
      }
    } else {
      // Queue message if not connected
      this.messageQueue.push(payload);
      if (!this.connected) {
        this.connect();
      }
    }
  }

  /**
   * Subscribe to messages by type
   */
  on(type: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => this.off(type, handler);
  }

  /**
   * Unsubscribe from messages
   */
  off(type: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Listen for connection state changes
   */
  onConnectionChange(callback: ConnectionCallback): () => void {
    this.connectionHandlers.add(callback);

    // Return unsubscribe function
    return () => this.connectionHandlers.delete(callback);
  }

  /**
   * Get current connection status
   */
  isConnected(): boolean {
    return this.connected;
  }

  // ========================================================================
  // Private Methods
  // ========================================================================

  private onOpen(): void {
    console.log('[WS] Connected');
    this.connected = true;
    this.retryCount = 0;

    // Flush queued messages
    const queued = [...this.messageQueue];
    this.messageQueue = [];
    for (const msg of queued) {
      this.ws?.send(msg);
    }

    // Notify listeners
    this.connectionHandlers.forEach((cb) => cb(true));

    // Start heartbeat monitor
    this.resetHeartbeatTimeout();
  }

  private onMessage(event: MessageEvent): void {
    this.resetHeartbeatTimeout();

    try {
      const message = JSON.parse(event.data) as BackendMessage;

      // Route to type-specific handlers
      const type = (message as unknown as Record<string, unknown>).type;
      if (type) {
        const handlers = this.messageHandlers.get(type as string);
        if (handlers) {
          handlers.forEach((handler) => handler(message));
        }
      }

      // Always emit to 'all' listeners
      const allHandlers = this.messageHandlers.get('all');
      if (allHandlers) {
        allHandlers.forEach((handler) => handler(message));
      }
    } catch (error) {
      console.error('[WS] Message parse error:', error, event.data);
    }
  }

  private onError(event: Event): void {
    console.error('[WS] Error:', event);
  }

  private onClose(): void {
    console.log('[WS] Closed');
    this.connected = false;

    // Notify listeners
    this.connectionHandlers.forEach((cb) => cb(false));

    // Attempt reconnect if we haven't exceeded max retries
    if (this.retryCount < this.maxRetries) {
      this.scheduleReconnect();
    } else {
      console.error('[WS] Max retries exceeded. Giving up.');
    }
  }

  private scheduleReconnect(): void {
    if (this.retryTimeoutId) {
      return; // Already scheduled
    }

    const delay = Math.min(this.retryDelay * Math.pow(2, this.retryCount), this.maxRetryDelay);
    this.retryCount++;

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})`);

    this.retryTimeoutId = setTimeout(() => {
      this.retryTimeoutId = null;
      this.connect();
    }, delay);
  }

  private resetHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutId) {
      clearTimeout(this.heartbeatTimeoutId);
    }

    this.heartbeatTimeoutId = setTimeout(() => {
      console.warn('[WS] No heartbeat received, reconnecting...');
      this.ws?.close();
      this.scheduleReconnect();
    }, this.heartbeatTimeout);
  }
}

// ============================================================================
// Singleton Instance & Export
// ============================================================================

let wsInstance: WebSocketManager | null = null;

export function getWebSocketManager(config?: WebSocketConfig): WebSocketManager {
  if (!wsInstance) {
    wsInstance = new WebSocketManager(config);
  }
  return wsInstance;
}

export function resetWebSocketManager(): void {
  if (wsInstance) {
    wsInstance.disconnect();
    wsInstance = null;
  }
}

export default WebSocketManager;
