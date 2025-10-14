import React from 'react';
import GlobalHeader from '../components/GlobalHeader';

const AppLayout: React.FC<{ children: React.ReactNode } & { onTradingActivityToggle?: () => void; showTradingActivity?: boolean }>
  = ({ children, onTradingActivityToggle, showTradingActivity }) => {
  return (
    <GlobalHeader onTradingActivityToggle={onTradingActivityToggle} showTradingActivity={showTradingActivity}>
      {children}
    </GlobalHeader>
  );
};

export default AppLayout;
