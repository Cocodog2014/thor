import { dispatch } from './router';
import type { ConnectionHandler, WsMessage } from './types';

const MAX_RETRIES = 10;
const INITIAL_DELAY = 1000;
const MAX_DELAY = 30000;
const HEARTBEAT_TIMEOUT = 15000;

let socket: WebSocket | null = null;
let retryCount = 0;
let retryTimeout: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
let connected = false;
let shouldReconnect = true;
const messageQueue: string[] = [];
const connectionHandlers = new Set<ConnectionHandler>();

function ensureTrailingSlash(url: string): string {
  return url.endsWith('/') ? url : `${url}/`;
}

function resolveUrl(): string {
  const explicit = import.meta.env.VITE_WS_URL;
  if (explicit) return ensureTrailingSlash(explicit);

  const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
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
}

function scheduleHeartbeatTimeout() {
  clearHeartbeat();
  heartbeatTimeout = setTimeout(() => {
    socket?.close();
  }, HEARTBEAT_TIMEOUT);
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
    if (payload) {
      socket.send(payload);
    }
  }
}

export function connectSocket(urlOverride?: string): void {
  if (socket && connected) return;
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

  socket.onopen = () => {
    connected = true;
    retryCount = 0;
    flushQueue();
    scheduleHeartbeatTimeout();
    notifyConnection(true);
  };

  socket.onmessage = (event) => {
    scheduleHeartbeatTimeout();
    try {
      const msg = JSON.parse(event.data) as WsMessage;
      dispatch(msg);
    } catch (err) {
      console.error('[ws] message parse error', err, event.data);
    }
  };

  socket.onerror = (event) => {
    console.error('[ws] error', event);
  };

  socket.onclose = () => {
    connected = false;
    clearHeartbeat();
    notifyConnection(false);
    if (shouldReconnect) {
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
  if (socket) {
    socket.close();
    socket = null;
  }
}

export function sendMessage(message: object): void {
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
