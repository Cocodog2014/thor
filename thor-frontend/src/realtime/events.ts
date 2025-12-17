export type ThorTopic =
  | "balances"
  | "positions"
  | "activityToday"
  | "orders"
  | "quotes";

export type ThorEvent =
  | { type: "snapshot"; topic: ThorTopic; accountId?: string; payload: unknown }
  | { type: "patch"; topic: ThorTopic; accountId?: string; payload: unknown; merge?: "replace" | "shallow" }
  | { type: "heartbeat"; ts: number }
  | { type: "error"; message: string };
