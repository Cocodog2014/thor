// src/pages/AccountStatements/AccountStatements.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import api from "../../services/api";
import { useSelectedAccount } from "../../context/SelectedAccountContext";
import { useAccountBalance } from "../../hooks/useAccountBalance";

type ColumnDef = {
  key: string;
  label: string;
  align?: 'left' | 'right';
};

type RowData = {
  id: string;
  symbol?: string;
  [key: string]: string | undefined;
};

type DateRange = {
  from: string;
  to: string;
};

interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  account_number?: string | null;
  display_name: string;
  currency: string;
  net_liq: string;
  cash: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}

interface TradeApiRow {
  id: number | string;
  symbol: string;
  side: string;
  quantity: string;
  price: string;
  commission: string;
  fees: string;
  exec_time: string;
  order?: number | null;
}

interface AccountStatementsResponse {
  account: AccountSummary;
  date_range: DateRange;
  cashSweep: RowData[];
  futuresCash: RowData[];
  equities: RowData[];
  pnlBySymbol: RowData[];
  trades: TradeApiRow[];
  summary: RowData[];
}

const formatDateOnly = (iso?: string) => {
  if (!iso) return '';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  });
};

const formatDateRangeLabel = (range?: DateRange) => {
  if (!range) return '';
  if (range.from === range.to) {
    return formatDateOnly(range.from);
  }
  return `${formatDateOnly(range.from)} → ${formatDateOnly(range.to)}`;
};

const formatExecTime = (iso?: string) => {
  if (!iso) return '';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

interface CollapsibleSectionProps {
  title: string;
  columns: ColumnDef[];
  rows: RowData[];
  defaultExpanded?: boolean;
  textFilter: string;
  symbolFilter: string;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  columns,
  rows,
  defaultExpanded = true,
  textFilter,
  symbolFilter,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const filteredRows = useMemo(() => {
    let result = rows;

    if (symbolFilter) {
      const sym = symbolFilter.toUpperCase();
      result = result.filter(
        (r) => !r.symbol || r.symbol.toUpperCase() === sym
      );
    }

    if (textFilter.trim()) {
      const q = textFilter.toLowerCase();
      result = result.filter((r) =>
        Object.values(r).some((val) => val && val.toLowerCase().includes(q))
      );
    }

    return result;
  }, [rows, symbolFilter, textFilter]);

  return (
    <section className="account-section">
      <button
        type="button"
        className="account-section-header"
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span className="account-section-toggle-icon">
          {expanded ? '▾' : '▸'}
        </span>
        <span className="account-section-title">{title}</span>
        <span className="account-section-rowcount">
          {filteredRows.length} row{filteredRows.length === 1 ? '' : 's'}
        </span>
      </button>

      {expanded && (
        <div className="account-statements-table-wrapper">
          <table className="account-statements-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={col.align === 'right' ? 'align-right' : ''}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="account-no-rows">
                    No rows match the current filters.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.id}>
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={col.align === 'right' ? 'align-right' : ''}
                      >
                        {row[col.key] ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

// ---- Shape of the API response ---------------------------------------

const AccountStatements: React.FC = () => {
  const { accountId } = useSelectedAccount();
  const { data: balance, isFetching: balanceLoading } = useAccountBalance(accountId, 5000);

  // Date filters
  const [rangeMode, setRangeMode] = useState<'daysBack' | 'custom'>('daysBack');
  const [daysBack, setDaysBack] = useState<number>(1);
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');

  // Row filters
  const [textFilter, setTextFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState<string>('');

  // Data state
  const [data, setData] = useState<AccountStatementsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number> = {};

      if (accountId) {
        params.account_id = accountId;
      }

      if (rangeMode === 'daysBack') {
        params.days_back = Math.max(1, daysBack);
      } else {
        if (fromDate) params.from = fromDate;
        if (toDate) params.to = toDate;
      }

      const res = await api.get<AccountStatementsResponse>(
        '/trades/account-statement',
        { params }
      );

      setData(res.data);
    } catch (err: unknown) {
      console.error('Failed to load account statements', err);
      setError('Unable to load account statements.');
    } finally {
      setLoading(false);
    }
  }, [accountId, rangeMode, daysBack, fromDate, toDate]);

  useEffect(() => {
    // Initial load
    loadData();
  }, [loadData]);

  const handleApplyFilters = () => {
    loadData();
  };

  const cashSweepRows = useMemo(() => data?.cashSweep ?? [], [data?.cashSweep]);
  const futuresCashRows = useMemo(() => data?.futuresCash ?? [], [data?.futuresCash]);
  const equitiesRows = useMemo(() => data?.equities ?? [], [data?.equities]);
  const pnlRows = useMemo(() => data?.pnlBySymbol ?? [], [data?.pnlBySymbol]);
  const summaryRows = useMemo(() => data?.summary ?? [], [data?.summary]);
  const accountSummary = data?.account;
  const dateRange = data?.date_range;

  const normalizedSummaryRows = useMemo(() => {
    if (balance) {
      return [
        { id: 'net_liq', metric: 'Net Liquidating Value', value: balance.net_liquidation?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'cash', metric: 'Cash', value: balance.cash?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'stock_bp', metric: 'Stock Buying Power', value: balance.buying_power?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'option_bp', metric: 'Option Buying Power', value: balance.buying_power?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'dt_bp', metric: 'Day Trading Buying Power', value: balance.day_trade_bp?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'equity', metric: 'Equity', value: balance.equity?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—' },
        { id: 'meta', metric: 'Source', value: `${balance.source || 'unknown'}${balance.updated_at ? ` · as of ${new Date(balance.updated_at).toLocaleTimeString()}` : ''}` },
      ];
    }

    return summaryRows;
  }, [balance, summaryRows]);

  const tradesRows = useMemo<RowData[]>(() => {
    if (!data?.trades) {
      return [];
    }
    return data.trades.map((trade, index) => ({
      id: trade.id ? String(trade.id) : `trade-${index}-${trade.exec_time}`,
      symbol: trade.symbol,
      side: trade.side,
      qty: trade.quantity,
      price: trade.price,
      commission: trade.commission,
      fees: trade.fees,
      execTime: formatExecTime(trade.exec_time),
      orderId: trade.order ? trade.order.toString() : undefined,
    }));
  }, [data?.trades]);

  const accountDisplayName =
    accountSummary?.display_name ||
    accountSummary?.broker_account_id ||
    'Active Account';
  const balanceAsOf = balance?.updated_at ? new Date(balance.updated_at).toLocaleString() : null;
  const dateRangeLabel = dateRange ? formatDateRangeLabel(dateRange) : 'Today';

  // Build symbol list from whatever sections make sense
  const allSymbols = useMemo(() => {
    const symbols = new Set<string>();
    [equitiesRows, pnlRows, tradesRows].forEach((section) => {
      section.forEach((row) => {
        if (row.symbol) symbols.add(row.symbol);
      });
    });
    return Array.from(symbols).sort();
  }, [equitiesRows, pnlRows, tradesRows]);

  return (
    <div className="account-statements-page">
      <header className="account-statements-header">
        <h1>Account Statements</h1>
        <p className="account-statements-subtitle">
          Snapshot of cash, positions, P&amp;L and account summary for the
          selected period.
        </p>
      </header>

      <section className="account-statements-meta">
        <div className="account-meta-item">
          <span className="account-meta-label">Account</span>
          <span className="account-meta-value">{accountDisplayName}</span>
        </div>
        <div className="account-meta-item">
          <span className="account-meta-label">Date Range</span>
          <span className="account-meta-value">{dateRangeLabel}</span>
        </div>
        <div className="account-meta-item">
          <span className="account-meta-label">Balance</span>
          <span className="account-meta-value">
            {balanceLoading ? 'Loading…' : balanceAsOf ? `As of ${balanceAsOf}` : 'Not available'}
          </span>
        </div>
      </section>

      {/* Statement for: filter bar */}
      <section className="account-statements-filters">
        <div className="filter-group wide">
          <span className="filter-group-label-main">Statement for:</span>

          <div className="statement-range-row">
            <label className="statement-range-option">
              <input
                type="radio"
                checked={rangeMode === 'daysBack'}
                onChange={() => setRangeMode('daysBack')}
              />
              <span className="statement-range-text">
                <input
                  type="number"
                  min={1}
                  value={daysBack}
                  onChange={(e) => setDaysBack(Number(e.target.value) || 1)}
                  className="statement-days-input"
                />
                <span>days back from</span>
                <select
                  className="account-statements-select statement-today-select"
                  value="today"
                  onChange={() => undefined}
                >
                  <option value="today">Today</option>
                </select>
              </span>
            </label>

            <label className="statement-range-option">
              <input
                type="radio"
                checked={rangeMode === 'custom'}
                onChange={() => setRangeMode('custom')}
              />
              <span className="statement-range-text">
                <span>from</span>
                <input
                  type="date"
                  className="account-statements-select statement-date-input"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  disabled={rangeMode !== 'custom'}
                />
                <span>to</span>
                <input
                  type="date"
                  className="account-statements-select statement-date-input"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  disabled={rangeMode !== 'custom'}
                />
              </span>
            </label>
          </div>

          <p className="statement-range-help">
            Maximum period length is 370 days.
          </p>
        </div>

        <button
          type="button"
          className="account-statements-apply-btn"
          onClick={handleApplyFilters}
        >
          Apply Filters
        </button>
      </section>

      {/* Row filter + show by symbol */}
      <section className="account-statements-subfilters">
        <div className="filter-group">
          <label htmlFor="row-filter-input">Filter rows</label>
          <input
            id="row-filter-input"
            type="text"
            className="account-statements-select account-row-filter-input"
            placeholder="Type to filter description / values"
            value={textFilter}
            onChange={(e) => setTextFilter(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="show-by-symbol-select">Show by symbol</label>
          <select
            id="show-by-symbol-select"
            className="account-statements-select"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
          >
            <option value="">All symbols</option>
            {allSymbols.map((sym) => (
              <option key={sym} value={sym}>
                {sym}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Loading / error states */}
      {loading && <div className="account-no-rows">Loading…</div>}
      {error && !loading && (
        <div className="account-no-rows" style={{ color: '#f97373' }}>
          {error}
        </div>
      )}

      {/* Sections (always render so the fields are visible) */}
      <section className="account-statements-sections">
        <CollapsibleSection
          title="Cash & Sweep Vehicle"
          columns={[
            { key: 'tradeDate', label: 'Trade Date' },
            { key: 'execDate', label: 'Exec Date' },
            { key: 'execTime', label: 'Exec Time' },
            { key: 'type', label: 'Type' },
            { key: 'description', label: 'Description' },
            { key: 'miscFees', label: 'Misc Fees', align: 'right' },
            { key: 'commissions', label: 'Commissions & Fees', align: 'right' },
            { key: 'amount', label: 'Amount', align: 'right' },
            { key: 'balance', label: 'Balance', align: 'right' },
          ]}
          rows={cashSweepRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />

        <CollapsibleSection
          title="Futures Cash Balance"
          columns={[
            { key: 'tradeDate', label: 'Trade Date' },
            { key: 'execDate', label: 'Exec Date' },
            { key: 'execTime', label: 'Exec Time' },
            { key: 'type', label: 'Type' },
            { key: 'description', label: 'Description' },
            { key: 'miscFees', label: 'Misc Fees', align: 'right' },
            { key: 'commissions', label: 'Commissions & Fees', align: 'right' },
            { key: 'amount', label: 'Amount', align: 'right' },
            { key: 'balance', label: 'Balance', align: 'right' },
          ]}
          rows={futuresCashRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />

        <CollapsibleSection
          title="Equities"
          columns={[
            { key: 'symbol', label: 'Symbol' },
            { key: 'description', label: 'Description' },
            { key: 'qty', label: 'Qty', align: 'right' },
            { key: 'tradePrice', label: 'Trade Price', align: 'right' },
            { key: 'mark', label: 'Mark', align: 'right' },
            { key: 'markValue', label: 'Mark Value', align: 'right' },
          ]}
          rows={equitiesRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />
        
        <CollapsibleSection
          title="Profits and Losses (by Symbol)"
          columns={[
            { key: 'symbol', label: 'Symbol' },
            { key: 'description', label: 'Description' },
            { key: 'plOpen', label: 'P/L Open', align: 'right' },
            { key: 'plPct', label: 'P/L %', align: 'right' },
            { key: 'plDay', label: 'P/L Day', align: 'right' },
            { key: 'plYtd', label: 'P/L YTD', align: 'right' },
          ]}
          rows={pnlRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />

        <CollapsibleSection
          title="Trades"
          columns={[
            { key: 'execTime', label: 'Exec Time' },
            { key: 'symbol', label: 'Symbol' },
            { key: 'side', label: 'Side' },
            { key: 'qty', label: 'Qty', align: 'right' },
            { key: 'price', label: 'Price', align: 'right' },
            { key: 'commission', label: 'Commission', align: 'right' },
            { key: 'fees', label: 'Fees', align: 'right' },
          ]}
          rows={tradesRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />

        <CollapsibleSection
          title="Account Summary"
          columns={[
            { key: 'metric', label: 'Metric' },
            { key: 'value', label: 'Value', align: 'right' },
          ]}
          rows={normalizedSummaryRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />
      </section>

    
    </div>
  );
};

export default AccountStatements;

