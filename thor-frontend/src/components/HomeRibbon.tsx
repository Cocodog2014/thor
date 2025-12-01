import React from 'react';
import './HomeRibbon.css';

// Moved to components so it can be globally mounted under banner.
const HomeRibbon: React.FC = () => {
  return (
    <div className="home-ribbon" aria-label="Market ticker ribbon">
      <div className="home-ribbon-track">
        🔔 Futures: ES +0.28% • NQ +0.34% • RTY +0.12% • CL -0.45% • GC +0.15% • DXY 104.6 • VIX 12.8 • BTC 98,450 • ETH 5,230 • AAPL 198.32 • MSFT 374.55 • NVDA 487.21 • TSLA 234.10 • AMZN 152.40 • META 328.02 • GOOG 138.25 • SPY 471.31 • QQQ 404.17 • IWM 186.42 • 10Y 4.27% • 2Y 4.52% •
        🔔 Futures: ES +0.28% • NQ +0.34% • RTY +0.12% • CL -0.45% • GC +0.15% • DXY 104.6 • VIX 12.8 • BTC 98,450 • ETH 5,230 • AAPL 198.32 • MSFT 374.55 • NVDA 487.21 • TSLA 234.10 • AMZN 152.40 • META 328.02 • GOOG 138.25 • SPY 471.31 • QQQ 404.17 • IWM 186.42 • 10Y 4.27% • 2Y 4.52% •
      </div>
    </div>
  );
};

export default HomeRibbon;
