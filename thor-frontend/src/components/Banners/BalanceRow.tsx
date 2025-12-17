// BalanceRow.tsx
import React from 'react';
import type { AccountBalance } from '../../hooks/useAccountBalance';

interface BalanceRowProps {
  balance: AccountBalance | undefined;
  loading: boolean;
}

const formatNumber = (value?: number) => {
  if (value === null || value === undefined) return '—';
  if (Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const BalanceRow: React.FC<BalanceRowProps> = ({ balance, loading }) => {
  const optionBp = balance?.buying_power;
  const stockBp = balance?.buying_power;
  const netLiq = balance?.net_liquidation;

  const asOf = balance?.updated_at ? new Date(balance.updated_at).toLocaleTimeString() : null;
  const source = balance?.source;

  return (
    <div className="global-banner-balances home-balances">
      <span>
        Option Buying Power:
        <span className="home-balance-value">
          {loading ? '…' : `$${formatNumber(optionBp)}`}
        </span>
      </span>
      <span>
        Stock Buying Power:
        <span className="home-balance-value">
          {loading ? '…' : `$${formatNumber(stockBp)}`}
        </span>
      </span>
      <span>
        Net Liq:
        <span className="home-balance-value">
          {loading ? '…' : `$${formatNumber(netLiq)}`}
        </span>
      </span>
      <span className="home-balance-meta">
        {loading ? 'Loading balance…' : source ? `${source}${asOf ? ` · as of ${asOf}` : ''}` : 'Balance source unknown'}
      </span>
    </div>
  );
};

export default BalanceRow;
