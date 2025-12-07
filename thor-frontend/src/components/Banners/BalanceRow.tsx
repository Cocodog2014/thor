// BalanceRow.tsx
import React from 'react';
import type { AccountSummary } from './bannerTypes';

interface BalanceRowProps {
  selectedAccount: AccountSummary | null;
  formatCurrency: (value?: string | null) => string;
}

const BalanceRow: React.FC<BalanceRowProps> = ({
  selectedAccount,
  formatCurrency,
}) => {
  return (
    <div className="global-banner-balances home-balances">
      <span>
        Option Buying Power:
        <span className="home-balance-value">
          {selectedAccount
            ? `$${formatCurrency(selectedAccount.option_buying_power)}`
            : '—'}
        </span>
      </span>
      <span>
        Stock Buying Power:
        <span className="home-balance-value">
          {selectedAccount
            ? `$${formatCurrency(selectedAccount.stock_buying_power)}`
            : '—'}
        </span>
      </span>
      <span>
        Net Liq:
        <span className="home-balance-value">
          {selectedAccount
            ? `$${formatCurrency(selectedAccount.net_liq)}`
            : '—'}
        </span>
      </span>
    </div>
  );
};

export default BalanceRow;
