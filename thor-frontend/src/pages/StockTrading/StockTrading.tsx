import { useMemo, useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import StockTradingDrawer from './StockTradingDrawer';

type TradingModeKey = 'live' | 'paper';

type MetricKey =
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

const metricBlueprint: { key: MetricKey; label: string }[] = [
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

const tradingModes: Record<TradingModeKey, {
  label: string;
  description: string;
  values: Record<MetricKey, { value: string; hint?: string }>;
}> = {
  live: {
    label: 'Live Trading',
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
    label: 'Paper Trading',
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

const StockTrading = () => {
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [mode, setMode] = useState<TradingModeKey>('live');
  const modeConfig = useMemo(() => {
    const base = tradingModes[mode];
    const metrics = metricBlueprint.map(({ key, label }) => ({
      label,
      ...base.values[key],
    }));
    return { ...base, metrics };
  }, [mode]);

  const handleModeChange = (value: TradingModeKey) => {
    setMode(value);
  };

  return (
    <Box className="stock-trading-wrapper">
      <Box className="stock-trading-page">
        <Box className="stock-trading-content">
          <Paper elevation={0} className="stock-trading-panel">
            <Box className="stock-trading-panel-header">
              <Typography variant="h5" className="stock-trading-title">
                {modeConfig.label}
              </Typography>
              <Typography variant="body2" className="stock-trading-description">
                {modeConfig.description}
              </Typography>
            </Box>

            <Box className="stock-metrics-list">
              {modeConfig.metrics.map(({ label, value, hint }) => (
                <Box key={label} className="stock-metric-row">
                  <Box className="stock-metric-text">
                    <Typography variant="body2" className="stock-metric-label">
                      {label}
                    </Typography>
                    {hint && (
                      <Typography variant="caption" className="stock-metric-hint">
                        {hint}
                      </Typography>
                    )}
                  </Box>
                  <Typography variant="body1" className="stock-metric-value">
                    {value}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Box>
      </Box>

      <StockTradingDrawer
        open={drawerOpen}
        onToggle={() => setDrawerOpen((prev) => !prev)}
        mode={mode}
        onModeChange={handleModeChange}
      />
    </Box>
  );
};

export default StockTrading;
