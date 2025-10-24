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
};

const AppLayout: React.FC<AppLayoutProps>
  = ({ children, onTradingActivityToggle, showTradingActivity, onAccountStatementToggle, showAccountStatement, onGlobalMarketToggle, showGlobalMarket }) => {
  return (
    <GlobalHeader 
      onTradingActivityToggle={onTradingActivityToggle} 
      showTradingActivity={showTradingActivity}
      onAccountStatementToggle={onAccountStatementToggle}
      showAccountStatement={showAccountStatement}
      onGlobalMarketToggle={onGlobalMarketToggle}
      showGlobalMarket={showGlobalMarket}
    >
      {children}
    </GlobalHeader>
  );
};

export default AppLayout;
