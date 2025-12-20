export const qk = {
  balances: (accountKey: string) => ["balances", accountKey] as const,
  positions: (accountKey: string) => ["positions", accountKey] as const,
  activityToday: (accountKey: string) => ["activityToday", accountKey] as const,
  orders: (accountKey: string) => ["orders", accountKey] as const,
  quotes: (accountKey: string) => ["quotes", accountKey] as const,
  globalMarkets: () => ["globalMarkets"] as const,
  marketStatus: () => ["marketStatus"] as const,
  heartbeat: () => ["heartbeat"] as const,
};
