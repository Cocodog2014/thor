import { useEffect, useRef, useState } from 'react';
import { subscribe } from './router';
import { connectSocket, disconnectSocket, sendMessage, onConnectionChange, isConnected } from './socket';
import type { MessageHandler } from './types';

// Public API
export { subscribe } from './router';
export type { MessageHandler, WsMessage } from './types';

// Socket facade for consumers that prefer an object
export const marketSocket = {
  connect: connectSocket,
  disconnect: disconnectSocket,
  send: sendMessage,
  onConnectionChange,
  isConnected,
};

// Hooks
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

// Friendly aliases to match the requested API
export const useChannel = useWsMessage;
export const useConnection = useWsConnection;
export const sendWsMessage = sendMessage;
export const connectWs = connectSocket;
export const disconnectWs = disconnectSocket;

export function getWsStatus() {
  return { connected: isConnected() };
}
