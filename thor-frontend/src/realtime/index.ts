import { connectSocket, disconnectSocket, sendMessage, onConnectionChange, isConnected } from './socket';

// Public API surface
export { subscribe } from './router';
export type { MessageHandler, WsMessage } from './types';
export { useWsMessage, useWsConnection, useChannel, useConnection } from './hooks';

// Socket facade for consumers that prefer an object
export const marketSocket = {
  connect: connectSocket,
  disconnect: disconnectSocket,
  send: sendMessage,
  onConnectionChange,
  isConnected,
};

// Friendly aliases to match requested API naming
export const sendWsMessage = sendMessage;
export const connectWs = connectSocket;
export const disconnectWs = disconnectSocket;

export function getWsStatus() {
  return { connected: isConnected() };
}
