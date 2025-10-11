import { useState } from 'react';
import { Box } from '@mui/material';
import StockTradingDrawer from './StockTradingDrawer';
import Account from './Account/Account';
import Positions from './Positions/Positions';
import WatchList from './WatchList/WatchList';
import MarketOverview from './MarketOverview/MarketOverview.tsx';
import NewsHeatmap from './NewsHeatmap/NewsHeatmap.tsx';
import { type TradingModeKey } from './Account/accountData';

const StockTrading = () => {
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [mode, setMode] = useState<TradingModeKey>('live');

  const handleModeChange = (value: TradingModeKey) => {
    setMode(value);
  };

  return (
    <Box className="stock-trading-wrapper">
      <Box className="stock-trading-page">
        <Box className="stock-trading-content">
          <Account mode={mode} />
          <Positions />
          <WatchList />
          <MarketOverview />
          <NewsHeatmap />
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
