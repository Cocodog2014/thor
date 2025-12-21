import { useEffect, useRef, useState } from 'react';
import { subscribe } from './router';
import { connectSocket, disconnectSocket, sendMessage, onConnectionChange, isConnected } from './socket';
import type { MessageHandler } from './types';

export { connectSocket, disconnectSocket, sendMessage } from './socket';
export { subscribe } from './router';
export type { MessageHandler } from './types';

export function useWsMessage(messageType: string, handler: MessageHandler, enabled = true): void {
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!enabled) return;
    connectSocket();
    const off = subscribe(messageType, (msg) => handlerRef.current(msg));
    return off;
  }, [messageType, enabled]);
}

export function useWsConnection(): boolean {
  const [state, setState] = useState(() => isConnected());

  useEffect(() => {
    connectSocket();
    const off = onConnectionChange(setState);
    return off;
  }, []);

  return state;
}
