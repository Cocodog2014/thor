import React, { useEffect, useMemo, useState } from 'react';
import './AccountStatement.css';
import { fetchAccountSummary, type AccountSummary, type AccountType } from '../../services/accountStatement';

const AccountStatement: React.FC = () => {
  const [accountType, setAccountType] = useState<AccountType>(() => {
    const saved = localStorage.getItem('thor_account_type');
    return (saved === 'real' || saved === 'paper') ? (saved as AccountType) : 'paper';
  });
  const [data, setData] = useState<AccountSummary>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    localStorage.setItem('thor_account_type', accountType);
    setLoading(true);
    fetchAccountSummary(accountType)
      .then(setData)
      .finally(() => setLoading(false));
  }, [accountType]);

  const rows = useMemo(() => ([
    { label: 'Net Liquidating Value', value: data.netLiquidatingValue || '' },
    { label: 'Stock Buying Power', value: data.stockBuyingPower || '' },
    { label: 'Option Buying Power', value: data.optionBuyingPower || '' },
    { label: 'Day Trading Buying Power', value: data.dayTradingBuyingPower || '' },
    { label: 'Available Funds For Trading', value: data.availableFundsForTrading || '' },
    { label: 'Long Stock Value', value: data.longStockValue || '' },
    { label: 'Equity Percentage', value: data.equityPercentage || '' },
  ]), [data]);

  return (
    <section className="dashboard-card account-statement" aria-label="Account Statement">
      <div className="as-header">
        <h3>Account Summary</h3>
        <div className="as-select">
          <label htmlFor="account-type" className="as-select-label">Mode</label>
          <select
            id="account-type"
            value={accountType}
            onChange={(e) => setAccountType(e.target.value as AccountType)}
            className="as-select-input"
          >
            <option value="paper">Paper trading</option>
            <option value="real">Real trading</option>
          </select>
        </div>
      </div>
      <div className="as-body">
        {loading ? (
          <div className="as-loading">Loading…</div>
        ) : (
          <table className="as-table">
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <td className="as-label">{r.label}</td>
                  <td className="as-value">{r.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};

export default AccountStatement;
