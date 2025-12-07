// bannerTypes.ts

export interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string;
  currency: string;
  net_liq: string;
  cash: string;
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
