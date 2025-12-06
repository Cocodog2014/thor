export interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string | null;
  currency: string;
  net_liq: string;
  cash: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}

export interface Order {
  id: number;
  symbol: string;
  asset_type: string;
  side: "BUY" | "SELL";
  quantity: string;
  order_type: string;
  limit_price: string | null;
  stop_price: string | null;
  status: string;
  time_placed: string;
  time_last_update: string;
  time_filled: string | null;
  time_canceled: string | null;
}

export interface Position {
  id: number;
  symbol: string;
  description: string;
  asset_type: string;
  quantity: string;
  avg_price: string;
  mark_price: string;
  market_value: string;
  unrealized_pl: string;
  pl_percent: string;
  realized_pl_open: string;
  realized_pl_day: string;
  currency: string;
}

export interface AccountStatus {
  ok_to_trade: boolean;
  net_liq: string | number;
  day_trading_buying_power: string | number;
}

export interface ActivityTodayResponse {
  account: AccountSummary;
  working_orders: Order[];
  filled_orders: Order[];
  canceled_orders: Order[];
  positions: Position[];
  account_status: AccountStatus;
}

export interface PaperOrderResponse {
  account: AccountSummary;
  order: Order;
  position: Position | null;
}
