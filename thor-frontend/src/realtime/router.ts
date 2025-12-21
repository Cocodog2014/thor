import type { MessageHandler, WsMessage } from './types';

const subscribers = new Map<string, Set<MessageHandler>>();

export function subscribe(messageType: string, handler: MessageHandler): () => void {
  if (!subscribers.has(messageType)) {
    subscribers.set(messageType, new Set());
  }
  subscribers.get(messageType)!.add(handler);

  return () => {
    subscribers.get(messageType)?.delete(handler);
  };
}

export function dispatch(message: WsMessage): void {
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
