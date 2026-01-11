import type { MessageHandler, WsEnvelope } from './types';

const subscribers = new Map<string, Set<MessageHandler>>();

let activeAccountId: string | null = null;

function toId(next: unknown): string | null {
  if (next === null || next === undefined) return null;
  const s = String(next).trim();
  return s ? s : null;
}

function extractAccountId(message: WsEnvelope): string | null {
  const direct = (message as unknown as { account_id?: unknown; accountId?: unknown }).account_id
    ?? (message as unknown as { account_id?: unknown; accountId?: unknown }).accountId;
  const directId = toId(direct);
  if (directId) return directId;

  const data = (message as unknown as { data?: unknown }).data;
  if (!data || typeof data !== 'object') return null;

  const record = data as Record<string, unknown>;
  return toId(record.account_id ?? record.accountId ?? record.account_hash);
}

function isAccountScopedType(type: string): boolean {
  // These topics should only update the currently-selected account view.
  return (
    type === 'balances' ||
    type === 'balance' ||
    type === 'positions' ||
    type === 'position' ||
    type === 'orders' ||
    type === 'order'
  );
}

export function setActiveAccountId(next: string | number | null): void {
  activeAccountId = toId(next);
}

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

  // Back-compat + stability: normalize legacy dotted event names to underscore.
  const normalizedType = type.includes('.') ? type.replaceAll('.', '_') : type;

  // Global account gate: ignore account-scoped events not meant for the active account.
  // This prevents paper events from mutating the live UI (and vice versa).
  if (activeAccountId && isAccountScopedType(normalizedType)) {
    const msgAccountId = extractAccountId(message);
    if (!msgAccountId || msgAccountId !== activeAccountId) return;
  }

  const handlers = subscribers.get(type);
  if (handlers) {
    handlers.forEach((fn) => fn(message));
  }

  // Also dispatch under the normalized name (without duplicating if unchanged).
  if (normalizedType !== type) {
    const normalizedHandlers = subscribers.get(normalizedType);
    if (normalizedHandlers) {
      normalizedHandlers.forEach((fn) => fn({ ...message, type: normalizedType }));
    }
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
