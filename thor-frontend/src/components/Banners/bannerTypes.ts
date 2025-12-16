// bannerTypes.ts

export interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string;
  currency: string;
  net_liq: string;
  cash: string;
  starting_balance: string;
  current_cash: string;
  equity: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}

export interface ParentTab {
  label: string;
  path: string;
  key: string;
}

export interface ChildTab {
  label: string;
  path: string;
}

export interface SchwabHealth {
  connected: boolean;
  broker: string;
  token_expired: boolean;
  expires_at?: number;
  seconds_until_expiry?: number;
  trading_enabled?: boolean;
  approval_state?: 'not_connected' | 'read_only' | 'trading_enabled';
  last_error: string | null;
}
