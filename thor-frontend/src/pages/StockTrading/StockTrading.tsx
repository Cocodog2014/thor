import { useState } from 'react';
import { Box, Typography } from '@mui/material';
import StockTradingDrawer from './StockTradingDrawer';
import { DEFAULT_WIDTH_CLOSED, DEFAULT_WIDTH_OPEN } from '../../components/CollapsibleDrawer';

const StockTrading = () => {
  const [drawerOpen, setDrawerOpen] = useState(true);
  const drawerWidth = drawerOpen ? DEFAULT_WIDTH_OPEN : DEFAULT_WIDTH_CLOSED;

  return (
    <Box className="stock-trading-wrapper">
      <Box
        className="stock-trading-page"
        sx={{
          marginRight: drawerWidth,
          transition: 'margin 200ms ease',
        }}
      >
        <Typography variant="overline" className="stock-trading-coming-soon">
          Rebuild In Progress
        </Typography>
        <Typography variant="h3" component="h1" gutterBottom className="stock-trading-title">
          Stock Trading
        </Typography>
        <Typography variant="body1" className="stock-trading-description">
          We are rebuilding the StockTrading experience. Check back soon for portfolio tools, live quotes, and
          trade analytics tailored for the THOR platform.
        </Typography>
      </Box>

      <StockTradingDrawer open={drawerOpen} onToggle={() => setDrawerOpen((prev) => !prev)} />
    </Box>
  );
};

export default StockTrading;
