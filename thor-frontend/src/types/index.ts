// Market-related types used across the app

export interface MarketCurrentTime {
  year: number;
  month: number;
  date: number;
  day: string; // e.g., 'Sun', 'Mon'
  formatted_24h: string; // HH:mm:ss
  datetime: string;
  utc_offset: string; // e.g., '+09:00'
  dst_active: boolean;
}

export interface MarketStatus {
  is_in_trading_hours: boolean;
  status: string; // 'OPEN' | 'CLOSED' | etc.
  current_state?: 'OPEN' | 'PREOPEN' | 'PRECLOSE' | 'CLOSED' | 'HOLIDAY_CLOSED';
  next_open_at?: string; // ISO datetime string
  next_close_at?: string; // ISO datetime string
  next_event?: 'open' | 'close';
  seconds_to_next_event?: number;
  is_holiday_today?: boolean;
}

export interface Market {
  id: number;
  country: string;
  display_name: string;
  timezone_name: string;
  market_open_time: string; // HH:mm:ss
  market_close_time: string; // HH:mm:ss
  status: string; // 'OPEN' | 'CLOSED'
  is_active: boolean;
  currency: string;
  current_time: MarketCurrentTime;
  market_status: MarketStatus;
  sort_order: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}