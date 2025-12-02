import React from 'react';
import GlobalHeader from '../components/GlobalHeader';
import GlobalBanner from '../components/GlobalBanner';
import { FooterRibbon } from '../components/Ribbons';

type AppLayoutProps = {
  children: React.ReactNode;
  onTradingActivityToggle?: () => void;
  showTradingActivity?: boolean;
  onAccountStatementToggle?: () => void;
  showAccountStatement?: boolean;
  onGlobalMarketToggle?: () => void;
  showGlobalMarket?: boolean;
  onFuturesOnHomeToggle?: () => void;
  showFuturesOnHome?: boolean;
};

const AppLayout: React.FC<AppLayoutProps>
  = ({ children, onTradingActivityToggle, showTradingActivity, onAccountStatementToggle, showAccountStatement, onGlobalMarketToggle, showGlobalMarket, onFuturesOnHomeToggle, showFuturesOnHome }) => {
  return (
    <GlobalHeader 
      onTradingActivityToggle={onTradingActivityToggle} 
      showTradingActivity={showTradingActivity}
      onAccountStatementToggle={onAccountStatementToggle}
      showAccountStatement={showAccountStatement}
      onGlobalMarketToggle={onGlobalMarketToggle}
      showGlobalMarket={showGlobalMarket}
      onFuturesOnHomeToggle={onFuturesOnHomeToggle}
      showFuturesOnHome={showFuturesOnHome}
    >
      {/* Layout: banner (top), scrollable content, ribbon (bottom) */}
      <GlobalBanner />
      <div className="app-content-scroll">
        {children}
      </div>
      <FooterRibbon />
    </GlobalHeader>
  );
};

export default AppLayout;
