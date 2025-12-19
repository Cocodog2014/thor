/**
 * React Hook for WebSocket Management
 *
 * Provides easy subscription to WebSocket events with cleanup
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { getWebSocketManager, BackendMessage, MessageHandler } from '../services/websocket';

/**
 * Hook to listen to a specific message type
 *
 * @param messageType - The type of message to listen for (e.g., 'market_status', 'intraday_bar')
 * @param handler - Callback function to handle the message
 * @param enabled - Whether to enable the listener (default: true)
 *
 * @example
 * useWebSocketMessage('market_status', (msg) => {
 *   console.log('Market status:', msg);
 * });
 */
export function useWebSocketMessage(
  messageType: string,
  handler: MessageHandler,
  enabled = true
): void {
  const wsManager = useRef(getWebSocketManager());
  const handlerRef = useRef(handler);

  // Update handler ref when it changes
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!enabled) return;

    const ws = wsManager.current;
    const wrappedHandler = (msg: BackendMessage) => handlerRef.current(msg);

    // Subscribe
    const unsubscribe = ws.on(messageType, wrappedHandler);

    // Cleanup
    return () => {
      unsubscribe();
    };
  }, [messageType, enabled]);
}

/**
 * Hook to listen to connection state changes
 *
 * @example
 * const isConnected = useWebSocketConnection();
 */
export function useWebSocketConnection(): boolean {
  const [connected, setConnected] = useState(false);
  const wsManager = useRef(getWebSocketManager());

  useEffect(() => {
    const ws = wsManager.current;
    setConnected(ws.isConnected());

    const unsubscribe = ws.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    return () => unsubscribe();
  }, []);

  return connected;
}

/**
 * Hook to send messages via WebSocket
 *
 * @example
 * const send = useWebSocketSend();
 * send({ type: 'subscribe', channel: 'prices' });
 */
export function useWebSocketSend(): (message: object) => void {
  const wsManager = useRef(getWebSocketManager());

  return useCallback((message: object) => {
    wsManager.current.send(message);
  }, []);
}

/**
 * Hook for complete WebSocket management in a component
 *
 * @example
 * const { connected, send, on } = useWebSocket();
 */
export function useWebSocket() {
  const wsManager = useRef(getWebSocketManager());
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = wsManager.current;
    setConnected(ws.isConnected());

    const unsubscribe = ws.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    return () => unsubscribe();
  }, []);

  return {
    connected,
    send: useCallback((message: object) => {
      wsManager.current.send(message);
    }, []),
    on: useCallback((type: string, handler: MessageHandler) => {
      return wsManager.current.on(type, handler);
    }, []),
    connect: useCallback(() => {
      wsManager.current.connect();
    }, []),
    disconnect: useCallback(() => {
      wsManager.current.disconnect();
    }, []),
  };
}

export default useWebSocketMessage;
