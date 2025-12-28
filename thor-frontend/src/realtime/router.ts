import type { MessageHandler, WsEnvelope } from './types';

const subscribers = new Map<string, Set<MessageHandler>>();

export function subscribe<T = unknown>(messageType: string, handler: MessageHandler<T>): () => void {
  if (!subscribers.has(messageType)) {
    subscribers.set(messageType, new Set());
  }
  subscribers.get(messageType)!.add(handler as MessageHandler);

  return () => {
    subscribers.get(messageType)?.delete(handler as MessageHandler);
  };
}

export function dispatch(message: WsEnvelope): void {
  const type = message?.type;
  if (!type) return;

  const handlers = subscribers.get(type);
  if (handlers) {
    handlers.forEach((fn) => fn(message));
  }

  const allHandlers = subscribers.get('all');
  if (allHandlers) {
    allHandlers.forEach((fn) => fn(message));
  }
}

// Alias for clarity with requested API shape
export function emit(type: string, message: WsEnvelope): void {
  dispatch({ ...message, type });
}
