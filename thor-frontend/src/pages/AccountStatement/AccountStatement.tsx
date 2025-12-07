// src/pages/AccountStatements/AccountStatements.tsx
import React, { useEffect, useMemo, useState } from 'react';
import api from "../../services/api";

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
// Adjust this to match what your backend actually sends.
interface AccountStatementsResponse {
  cashSweep: RowData[];
  futuresCash: RowData[];
  equities: RowData[];
  pnlBySymbol: RowData[];
  summary: RowData[];
}

const AccountStatements: React.FC = () => {
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

  // For now, pick the active account however you do it elsewhere
  const [accountId] = useState<string>('PRIMARY'); // TODO: wire to real account selector

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = { accountId };

      if (rangeMode === 'daysBack') {
        params.daysBack = daysBack;
      } else {
        if (fromDate) params.from = fromDate;
        if (toDate) params.to = toDate;
      }

      const res = await api.get<AccountStatementsResponse>(
        '/account-statements',
        { params }
      );

      setData(res.data);
    } catch (err: any) {
      console.error('Failed to load account statements', err);
      setError('Unable to load account statements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]);

  const handleApplyFilters = () => {
    loadData();
  };

  const cashSweepRows = data?.cashSweep ?? [];
  const futuresCashRows = data?.futuresCash ?? [];
  const equitiesRows = data?.equities ?? [];
  const pnlRows = data?.pnlBySymbol ?? [];
  const summaryRows = data?.summary ?? [];

  // Build symbol list from whatever sections make sense
  const allSymbols = useMemo(() => {
    const symbols = new Set<string>();
    [equitiesRows, pnlRows].forEach((section) => {
      section.forEach((row) => {
        if (row.symbol) symbols.add(row.symbol);
      });
    });
    return Array.from(symbols).sort();
  }, [equitiesRows, pnlRows]);

  return (
    <div className="account-statements-page">
      <header className="account-statements-header">
        <h1>Account Statements</h1>
        <p className="account-statements-subtitle">
          Snapshot of cash, positions, P&amp;L and account summary for the
          selected period.
        </p>
      </header>

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

