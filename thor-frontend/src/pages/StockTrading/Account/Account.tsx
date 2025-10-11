import { Box, Paper, Typography } from '@mui/material';
import {
  metricBlueprint,
  tradingModeData,
  type TradingModeKey,
  type MetricKey,
} from './accountData';

export type Metric = {
  key: MetricKey;
  label: string;
  value: string;
  hint?: string;
};

interface AccountProps {
  mode: TradingModeKey;
}

const Account: React.FC<AccountProps> = ({ mode }) => {
  const config = tradingModeData[mode];
  const metrics: Metric[] = metricBlueprint.map(({ key, label }) => ({
    key,
    label,
    ...config.values[key],
  }));

  const compactMetricKeys = new Set<MetricKey>(metricBlueprint.map(({ key }) => key));

  return (
    <Paper elevation={0} className="account-panel">
      <Box className="account-panel-header">
        <Typography variant="h5" className="account-title">
          {config.title}
        </Typography>
        <Typography variant="body2" className="account-description">
          {config.description}
        </Typography>
      </Box>

      <Box className="account-metrics-list">
        {metrics.map(({ key, label, value, hint }) => {
          const rowClass = compactMetricKeys.has(key)
            ? 'account-metric-row account-metric-row--compact'
            : 'account-metric-row';

          return (
            <Box key={label} className={rowClass}>
              <Box className="account-metric-text">
                <Typography variant="body2" className="account-metric-label">
                  {label}
                </Typography>
                {hint && (
                  <Typography variant="caption" className="account-metric-hint">
                    {hint}
                  </Typography>
                )}
              </Box>
              <Typography variant="body1" className="account-metric-value">
                {value}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Paper>
  );
};

export default Account;
