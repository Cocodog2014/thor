import { useEffect, useRef, useState } from 'react';
import { subscribe } from './router';
import { connectSocket, onConnectionChange, isConnected, wsEnabled } from './socket';
import type { MessageHandler, WsEnvelope } from './types';

export function useWsMessage<T = unknown>(
  messageType: string,
  handler: MessageHandler<T>,
  enabled = true
): void {
  const handlerRef = useRef<MessageHandler<T>>(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    // If WS is disabled globally, do nothing (NO CONNECT)
    if (!wsEnabled()) return;

    // Local per-hook toggle
    if (!enabled) return;

    connectSocket();
    const off = subscribe<T>(messageType, (msg: WsEnvelope<T>) => handlerRef.current(msg));
    return off;
  }, [messageType, enabled]);
}

export function useWsConnection(enabled = true): boolean {
  const [state, setState] = useState(() => isConnected());

  useEffect(() => {
    // If WS is disabled globally, do nothing (NO CONNECT)
    if (!wsEnabled()) return;

    if (!enabled) return;

    connectSocket();
    const off = onConnectionChange(setState);
    return off;
  }, [enabled]);

  return state;
}

// Friendly aliases for downstream code
export const useChannel = useWsMessage;
export const useConnection = useWsConnection;

