export type GlobalMarketStatus = 'OPEN' | 'CLOSED' | string;

// REST: GET /api/global-markets/markets/
export type GlobalMarket = {
  id: number;
  key: string;
  name: string;
  status: GlobalMarketStatus;
  status_changed_at?: string | null;
  next_transition_utc?: string | null;
};

// WS: type=global_markets_tick
export type GlobalMarketsTickPayload = {
  server_time_utc?: string;
  markets?: Array<{
    key: string;
    name?: string;
    status: GlobalMarketStatus;
    next_transition_utc?: string | null;
  }>;
};
