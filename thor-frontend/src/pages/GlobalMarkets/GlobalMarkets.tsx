import React from 'react';
import { useGlobalMarkets } from '../../features/globalMarkets/useGlobalMarkets';
import './GlobalMarkets.css';

import type { Market } from '../../types';

const GlobalMarkets: React.FC = () => {
  const { markets, loading, error, lastUpdate, isStale } = useGlobalMarkets();

  if (loading) {
    return (
      <div className="timezone-container">
        <div className="markets-table-container">
          <div className="markets-table-header">
            <div className="last-update">Loading…</div>
          </div>
          <div className="market-loading">Loading market data...</div>
        </div>
      </div>
    );
  }

  const formatUtc = (iso: string | null | undefined) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('en-US', {
      timeZone: 'UTC',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatLocal = (tz: string | null | undefined) => {
    if (!tz) return '—';
    const now = new Date();
    try {
      return new Intl.DateTimeFormat('en-US', {
        timeZone: tz,
        weekday: 'short',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(now);
    } catch {
      return '—';
    }
  };

  const formatUtcTime = (d: Date | null) =>
    d
      ? d.toLocaleTimeString('en-US', {
          timeZone: 'UTC',
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      : '—';

  const activeCount = markets.filter((m: Market) => String(m.status).toUpperCase() === 'OPEN').length;
  const totalCount = markets.length;

  return (
    <div className="timezone-container">
      {error && <div className="error-message">⚠️ {error}</div>}
      <div className="markets-table-container">
        <div className="markets-table-header">
          <div className="last-update">
            <span className="live-indicator" title={isStale ? 'Reconnecting…' : 'Live'}>
              {isStale ? '🟡' : '🟢'}
            </span>
            {' '}
            UTC time: {formatUtcTime(lastUpdate)}
            {' • '}Last update: {formatUtcTime(lastUpdate)}
          </div>
          <div className="markets-table-status">
            <span>
              Active: {activeCount}/{totalCount}
            </span>
          </div>
        </div>
        <table className="markets-table">
          <colgroup>
            <col className="col-market" />
            <col className="col-tz" />
            <col className="col-local" />
            <col className="col-open" />
            <col className="col-close" />
            <col className="col-status" />
            <col className="col-next" />
          </colgroup>
          <thead>
            <tr>
              <th>MARKET</th>
              <th>TZ</th>
              <th>LOCAL</th>
              <th>OPEN</th>
              <th>CLOSE</th>
              <th>STATUS</th>
              <th>NEXT (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((market: Market) => {
              const status = String(market.status ?? 'UNKNOWN').toUpperCase();
              const isOpen = status === 'OPEN';
              const statusColor = isOpen ? 'open' : 'closed';
              const title = market.key ? `${market.key} • ${market.timezone_name ?? ''}` : market.timezone_name ?? '';
              const displayName = market.display_name ?? market.name ?? '—';
              return (
                <tr
                  key={market.id ?? market.key ?? displayName}
                  className={statusColor}
                  title={title}
                >
                  <td className="market-name">{displayName}</td>
                  <td className="market-tz">{market.timezone_name ?? '—'}</td>
                  <td className="market-local">{formatLocal(market.timezone_name)}</td>
                  <td className="market-open">{market.market_open_time ?? '—'}</td>
                  <td className="market-close">{market.market_close_time ?? '—'}</td>
                  <td className="market-status">
                    <span className={`status-indicator ${statusColor}`}>{status}</span>
                  </td>
                  <td className="market-next">{formatUtc(market.next_transition_utc)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default GlobalMarkets;
