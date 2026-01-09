import { dispatch } from './router';
import type { ConnectionHandler, WsMessage } from './types';

// WS hard gate (OFF by default)
// Enable by setting: VITE_WS_ENABLED=1 (or true)
function isWsEnabled(): boolean {
  // If you ever want a runtime toggle in DevTools:
  // window.__THOR_WS_ENABLED__ = true
  const w = typeof window !== 'undefined'
    ? (window as unknown as { __THOR_WS_ENABLED__?: boolean })
    : undefined;
  if (w?.__THOR_WS_ENABLED__ === true) return true;

  const env = String(import.meta.env?.VITE_WS_ENABLED ?? '').toLowerCase();
  return env === '1' || env === 'true' || env === 'yes';
}

// AUTH-ONLY MODE: Never connect on /auth routes
function isAuthRoute(): boolean {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/auth');
}

const MAX_RETRIES = 10;
const INITIAL_DELAY = 1000;
const MAX_DELAY = 30000;

// Heartbeat / idle detection
const IDLE_PING_AFTER_MS = 15000;
const PONG_GRACE_MS = 5000;

let socket: WebSocket | null = null;
let retryCount = 0;
let retryTimeout: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
let pongTimeout: ReturnType<typeof setTimeout> | null = null;
let connected = false;
let shouldReconnect = true;
const messageQueue: string[] = [];
const connectionHandlers = new Set<ConnectionHandler>();
let missedPongs = 0;

function ensureTrailingSlash(url: string): string {
  return url.endsWith('/') ? url : `${url}/`;
}

function resolveUrl(): string {
  const explicit = import.meta.env?.VITE_WS_URL;
  if (explicit) return ensureTrailingSlash(explicit);

  const protocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const port = window.location.port;

    if (host === 'localhost' || host === '127.0.0.1') {
      return `${protocol}://localhost:8000/ws/`;
    }

    const base = `${host}${port ? `:${port}` : ''}`;
    return `${protocol}://${base}/ws/`;
  }

  return `${protocol}://localhost:8000/ws/`;
}

function notifyConnection(state: boolean) {
  connectionHandlers.forEach((fn) => fn(state));
}

function clearHeartbeat() {
  if (heartbeatTimeout) {
    clearTimeout(heartbeatTimeout);
    heartbeatTimeout = null;
  }
  if (pongTimeout) {
    clearTimeout(pongTimeout);
    pongTimeout = null;
  }
}

function scheduleHeartbeatTimeout() {
  clearHeartbeat();

  heartbeatTimeout = setTimeout(() => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    try {
      socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
    } catch {
      socket.close();
      return;
    }

    pongTimeout = setTimeout(() => {
      missedPongs += 1;
      if (missedPongs >= 3) {
        socket?.close();
        return;
      }
      scheduleHeartbeatTimeout();
    }, PONG_GRACE_MS);
  }, IDLE_PING_AFTER_MS);
}

function scheduleReconnect(url: string) {
  if (retryTimeout || retryCount >= MAX_RETRIES) return;

  const delay = Math.min(INITIAL_DELAY * Math.pow(2, retryCount), MAX_DELAY);
  retryCount += 1;

  retryTimeout = setTimeout(() => {
    retryTimeout = null;
    connectSocket(url);
  }, delay);
}

function flushQueue() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  while (messageQueue.length) {
    const payload = messageQueue.shift();
    if (payload) socket.send(payload);
  }
}

export function connectSocket(urlOverride?: string): void {
  // HARD GATE: never connect unless explicitly enabled
  if (!isWsEnabled()) return;

  // AUTH ROUTES: never connect
  if (isAuthRoute()) return;

  // Already open/connecting? Don't create another
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  // Drop stale closed socket
  if (socket && socket.readyState === WebSocket.CLOSED) {
    socket = null;
  }

  const url = urlOverride || resolveUrl();

  shouldReconnect = true;

  if (retryTimeout) {
    clearTimeout(retryTimeout);
    retryTimeout = null;
  }

  try {
    socket = new WebSocket(url);
  } catch (err) {
    console.error('[ws] failed to construct socket', err);
    scheduleReconnect(url);
    return;
  }

  const currentSocket = socket;

  currentSocket.onopen = () => {
    connected = true;
    retryCount = 0;
    missedPongs = 0;
    flushQueue();
    scheduleHeartbeatTimeout();
    notifyConnection(true);
  };

  currentSocket.onmessage = (event) => {
    missedPongs = 0;
    scheduleHeartbeatTimeout();
    try {
      const msg = JSON.parse(event.data) as WsMessage;
      dispatch(msg);
    } catch (err) {
      console.error('[ws] message parse error', err, event.data);
    }
  };

  currentSocket.onerror = (event) => {
    console.error('[ws] error', event);
  };

  currentSocket.onclose = () => {
    connected = false;
    clearHeartbeat();
    missedPongs = 0;
    notifyConnection(false);

    if (socket === currentSocket) socket = null;

    if (shouldReconnect && isWsEnabled() && !isAuthRoute()) {
      scheduleReconnect(url);
    }
  };
}

export function disconnectSocket(): void {
  shouldReconnect = false;
  clearHeartbeat();

  if (retryTimeout) {
    clearTimeout(retryTimeout);
    retryTimeout = null;
  }

  retryCount = 0;
  missedPongs = 0;

  if (socket) {
    socket.close();
    socket = null;
  }
}

export function sendMessage(message: object): void {
  // HARD GATE: never send unless enabled
  if (!isWsEnabled()) return;

  if (isAuthRoute()) return;

  const payload = JSON.stringify(message);

  if (socket && socket.readyState === WebSocket.OPEN && connected) {
    socket.send(payload);
    return;
  }

  messageQueue.push(payload);
  connectSocket();
}

export function onConnectionChange(handler: ConnectionHandler): () => void {
  connectionHandlers.add(handler);
  return () => connectionHandlers.delete(handler);
}

export function isConnected(): boolean {
  return connected;
}

// Export gate so hooks/UI can respect it too
export function wsEnabled(): boolean {
  return isWsEnabled();
}
