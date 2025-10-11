export type TradingModeKey = 'live' | 'paper';

export type MetricKey =
  | 'longStockValue'
  | 'maintenanceRequirement'
  | 'marginBalance'
  | 'marginEquity'
  | 'moneyMarketBalance'
  | 'netLiquidatingValue'
  | 'optionBuyingPower'
  | 'settledFunds'
  | 'shortBalance'
  | 'shortMarginableValue'
  | 'stockBuyingPower'
  | 'totalCommissionsFeesYtd';

export interface MetricValue {
  value: string;
  hint?: string;
}

export const metricBlueprint: { key: MetricKey; label: string }[] = [
  { key: 'longStockValue', label: 'Long Stock Value' },
  { key: 'maintenanceRequirement', label: 'Maintenance Requirement' },
  { key: 'marginBalance', label: 'Margin Balance' },
  { key: 'marginEquity', label: 'Margin Equity' },
  { key: 'moneyMarketBalance', label: 'Money Market Balance' },
  { key: 'netLiquidatingValue', label: 'Net Liquidating Value' },
  { key: 'optionBuyingPower', label: 'Option Buying Power' },
  { key: 'settledFunds', label: 'Settled Funds' },
  { key: 'shortBalance', label: 'Short Balance' },
  { key: 'shortMarginableValue', label: 'Short Marginable Value' },
  { key: 'stockBuyingPower', label: 'Stock Buying Power' },
  { key: 'totalCommissionsFeesYtd', label: 'Total Commissions & Fees YTD' },
];

export const tradingModeData: Record<TradingModeKey, {
  title: string;
  description: string;
  values: Record<MetricKey, MetricValue>;
}> = {
  live: {
    title: 'Live Trading',
    description: 'Connected to primary brokerage account.',
    values: {
      longStockValue: { value: '$85,919.32' },
      maintenanceRequirement: { value: '$85,919.32' },
      marginBalance: { value: '$301.95' },
      marginEquity: { value: '$86,219.29' },
      moneyMarketBalance: { value: '$0.00' },
      netLiquidatingValue: { value: '$86,219.32' },
      optionBuyingPower: { value: '$300.00' },
      settledFunds: { value: '$0.03' },
      shortBalance: { value: '$0.00' },
      shortMarginableValue: { value: '$0.00' },
      stockBuyingPower: { value: '$295.38' },
      totalCommissionsFeesYtd: { value: '$3.71' },
    },
  },
  paper: {
    title: 'Paper Trading',
    description: 'Strategy testing.',
    values: {
      longStockValue: { value: '$150,000.00' },
      maintenanceRequirement: { value: '$75,000.00' },
      marginBalance: { value: '$0.00' },
      marginEquity: { value: '$150,000.00' },
      moneyMarketBalance: { value: '$25,000.00' },
      netLiquidatingValue: { value: '$175,000.00' },
      optionBuyingPower: { value: '$50,000.00' },
      settledFunds: { value: '$10,000.00' },
      shortBalance: { value: '$0.00' },
      shortMarginableValue: { value: '$0.00' },
      stockBuyingPower: { value: '$125,000.00' },
      totalCommissionsFeesYtd: { value: '$0.00', hint: 'No live fills in paper mode' },
    },
  },
};
