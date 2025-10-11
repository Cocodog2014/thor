import { Paper, Typography, Box } from '@mui/material';

const MarketOverview = () => {
  return (
    <Paper elevation={0} className="market-overview-panel">
      <Box className="market-overview-header">
        <Typography variant="h5" className="market-overview-title">
          Market Overview
        </Typography>
        <Typography variant="body2" className="market-overview-subtitle">
          Major indices snapshot
        </Typography>
      </Box>
      <Box className="market-overview-placeholder">
        <Typography variant="body2">
          Indices heatmap coming soon.
        </Typography>
      </Box>
    </Paper>
  );
};

export default MarketOverview;
