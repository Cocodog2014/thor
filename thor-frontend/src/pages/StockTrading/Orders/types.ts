export type QuoteTrend = 'up' | 'down' | 'flat';

export interface WatchListSymbol {
  symbol: string;
  description: string;
  last: string;
  netChange: string;
  open: string;
  bid: string;
  ask: string;
  size: string;
  volume: string;
  high: string;
  low: string;
  fiftyTwoWeekHigh: string;
  fiftyTwoWeekLow: string;
  quoteTrend: QuoteTrend;
  bidX: string;
  askX: string;
  lastX: string;
}

export interface ReviewOrderDetails {
  side: 'buy' | 'sell';
  orderType: 'limit' | 'market';
  timeInForce: 'day' | 'gtc';
  limitPrice: number;
  shares: number;
  notional: number;
}
