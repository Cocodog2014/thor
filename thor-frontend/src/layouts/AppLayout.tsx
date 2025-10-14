import React from 'react';
import GlobalHeader from '../components/GlobalHeader';

type AppLayoutProps = {
  children: React.ReactNode;
  onTradingActivityToggle?: () => void;
  showTradingActivity?: boolean;
  onAccountStatementToggle?: () => void;
  showAccountStatement?: boolean;
};

const AppLayout: React.FC<AppLayoutProps>
  = ({ children, onTradingActivityToggle, showTradingActivity, onAccountStatementToggle, showAccountStatement }) => {
  return (
    <GlobalHeader 
      onTradingActivityToggle={onTradingActivityToggle} 
      showTradingActivity={showTradingActivity}
      onAccountStatementToggle={onAccountStatementToggle}
      showAccountStatement={showAccountStatement}
    >
      {children}
    </GlobalHeader>
  );
};

export default AppLayout;
