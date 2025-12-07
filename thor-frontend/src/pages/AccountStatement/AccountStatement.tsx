// src/pages/AccountStatements/AccountStatements.tsx
import React, { useMemo, useState } from 'react';

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
      result = result.filter(
        (r) => !r.symbol || r.symbol.toUpperCase() === symbolFilter.toUpperCase()
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

const AccountStatements: React.FC = () => {
  // Date filters (the popup-like control from your screenshot)
  const [rangeMode, setRangeMode] = useState<'daysBack' | 'custom'>('daysBack');
  const [daysBack, setDaysBack] = useState<number>(1);
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');

  // Row filters
  const [textFilter, setTextFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState<string>('');

  // --- MOCK DATA FOR NOW (wire to backend later) -------------------------
  const cashSweepRows: RowData[] = [
    {
      id: 'cash-1',
      symbol: '',
      tradeDate: '12/6/25',
      execDate: '12/6/25',
      execTime: '23:00:00',
      type: 'BAL',
      description: 'Cash balance at the start of business day 07.12 CST',
      miscFees: '—',
      commissions: '—',
      amount: '$7.41',
      balance: '$7.41',
    },
  ];

  const futuresCashRows: RowData[] = [
    {
      id: 'futures-cash-1',
      symbol: '',
      tradeDate: '12/6/25',
      execDate: '12/6/25',
      execTime: '23:00:00',
      type: 'BAL',
      description: 'Futures cash balance at the start of business day 07.12 CST',
      miscFees: '—',
      commissions: '—',
      amount: '$0.00',
      balance: '$0.00',
    },
  ];

  const equitiesRows: RowData[] = [
    {
      id: 'VFF',
      symbol: 'VFF',
      description: 'VILLAGE FARMS INTL I',
      qty: '+26,740',
      tradePrice: '1.2179',
      mark: '3.37',
      markValue: '$90,113.80',
    },
    {
      id: 'CGC',
      symbol: 'CGC',
      description: 'CANOPY GROWTH CORP',
      qty: '+1',
      tradePrice: '3.7197',
      mark: '1.15',
      markValue: '$1.15',
    },
  ];

  const pnlRows: RowData[] = [
    {
      id: 'pnl-CGC',
      symbol: 'CGC',
      description: 'CANOPY GROWTH CORP',
      plOpen: '($2.57)',
      plPct: '-69.09%',
      plDay: '$0.00',
      plYtd: '($1,455.09)',
    },
    {
      id: 'pnl-VFF',
      symbol: 'VFF',
      description: 'VILLAGE FARMS INTL I',
      plOpen: '$57,548.38',
      plPct: '+176.72%',
      plDay: '$534.80',
      plYtd: '$68,209.80',
    },
    {
      id: 'pnl-total',
      symbol: '',
      description: 'OVERALL TOTALS',
      plOpen: '$57,545.81',
      plPct: '+176.69%',
      plDay: '$534.80',
      plYtd: '$66,754.71',
    },
  ];

  const summaryRows: RowData[] = [
    { id: 'sum-1', metric: 'Net Liquidating Value', value: '$90,122.36' },
    { id: 'sum-2', metric: 'Stock Buying Power', value: '$7.41' },
    { id: 'sum-3', metric: 'Day Trading Buying Power', value: '$7.41' },
    { id: 'sum-4', metric: 'Available Funds For Trading', value: '$7.41' },
    { id: 'sum-5', metric: 'Long Stock Value', value: '$90,114.95' },
    { id: 'sum-6', metric: 'Margin Equity', value: '$90,122.36' },
    { id: 'sum-7', metric: 'Equity Percentage', value: '100.00%' },
    { id: 'sum-8', metric: 'Maintenance Requirement', value: '$90,114.95' },
  ];
  // ----------------------------------------------------------------------

  // Build symbol list for Show-by-symbol dropdown
  const allSymbols = useMemo(() => {
    const symbols = new Set<string>();
    [equitiesRows, pnlRows].forEach((section) => {
      section.forEach((row) => {
        if (row.symbol) symbols.add(row.symbol);
      });
    });
    return Array.from(symbols).sort();
  }, [equitiesRows, pnlRows]);

  const handleApplyFilters = () => {
    // For now this is just a visual control.
    // Later you can trigger a backend fetch with the current date filters.
    console.log('Apply filters', { rangeMode, daysBack, fromDate, toDate });
  };

  return (
    <div className="account-statements-page">
      <header className="account-statements-header">
        <h1>Account Statements</h1>
        <p className="account-statements-subtitle">
          Snapshot of cash, positions, P&amp;L and account summary for the
          selected period.
        </p>
      </header>

      {/* This sits directly under your child buttons: Activity / Positions / Account Statements */}
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
            Maximum period length is 370 days. (Backend wiring coming soon.)
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

      {/* Row filter + Show-by-symbol (like your “Show by symbol: VFF” control) */}
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

      {/* Collapsible sections that look like the TOS panes */}
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
          title="Account Summary"
          columns={[
            { key: 'metric', label: 'Metric' },
            { key: 'value', label: 'Value', align: 'right' },
          ]}
          rows={summaryRows}
          textFilter={textFilter}
          symbolFilter={symbolFilter}
        />
      </section>
    </div>
  );
};

export default AccountStatements;
