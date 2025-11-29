export type Instrument = {
  id: number;
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  display_precision: number;
  tick_value: string | null;
  margin_requirement: string | null;
  is_active: boolean;
  sort_order: number;
};

export type SignalKey =
  | "STRONG_BUY"
  | "BUY"
  | "HOLD"
  | "SELL"
  | "STRONG_SELL";

export type MarketData = {
  instrument: Instrument;
  price: string | null;
  bid: string | null;
  ask: string | null;
  last_size: number | null;
  bid_size: number | null;
  ask_size: number | null;
  open_price: string | null;
  high_price: string | null;
  low_price: string | null;
  close_price: string | null;
  previous_close: string | null;
  change: string | null;
  change_percent: string | null;
  vwap: string | null;
  volume: number | null;
  market_status: "OPEN" | "CLOSED" | "PREMARKET" | "AFTERHOURS" | "HALT";
  data_source: string;
  is_real_time: boolean;
  delay_minutes: number;
  extended_data: {
    signal?: SignalKey;
    stat_value?: string;
    contract_weight?: string;
    signal_weight?: number;
    high_52w?: string | number | null;
    low_52w?: string | number | null;
  } & Record<string, unknown>;
  timestamp: string;
  last_prev_diff?: string | number | null;
  last_prev_pct?: string | number | null;
  open_prev_diff?: string | number | null;
  open_prev_pct?: string | number | null;
  range_diff?: string | number | null;
  range_pct?: string | number | null;
  last_52w_above_low_diff?: string | number | null;
  last_52w_above_low_pct?: string | number | null;
  last_52w_below_high_diff?: string | number | null;
  last_52w_below_high_pct?: string | number | null;
} & Record<string, unknown>;

export type ApiResponse = {
  rows: MarketData[];
  total: {
    sum_weighted: string;
    avg_weighted: string | null;
    count?: number;
    instrument_count?: number;
    denominator: string;
    as_of: string;
    signal_weight_sum?: number;
    composite_signal?: SignalKey;
    composite_signal_weight?: number;
  };
};

export type RoutingFeed = {
  code: string;
  display_name: string;
  connection_type: string;
  provider_key?: string;
  priority: number;
  is_primary: boolean;
};

export type RoutingPlanResponse = {
  consumer: {
    code: string;
    display_name: string;
  };
  primary_feed: RoutingFeed | null;
  feeds: RoutingFeed[];
};

export type FutureRTDProps = {
  onToggleMarketOpen?: () => void;
  showMarketOpen?: boolean;
};

export type TotalData = ApiResponse["total"];
