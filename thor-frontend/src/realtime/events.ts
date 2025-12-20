export type ThorTopic =
  | "balances"
  | "positions"
  | "activityToday"
  | "orders"
  | "quotes"
  | "globalMarkets"
  | "marketStatus"
  | "heartbeat";

export type ThorEvent =
  | { type: "snapshot"; topic: ThorTopic; accountId?: string; payload: unknown }
  | { type: "patch"; topic: ThorTopic; accountId?: string; payload: unknown; merge?: "replace" | "shallow" }
  | { type: "heartbeat"; ts: number; topic?: ThorTopic; payload?: unknown; accountId?: string }
  | { type: "error"; message: string; accountId?: string };
