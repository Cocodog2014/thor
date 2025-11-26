import React from 'react';
import GlobalHeader from '../components/GlobalHeader';

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
      {children}
    </GlobalHeader>
  );
};

export default AppLayout;
