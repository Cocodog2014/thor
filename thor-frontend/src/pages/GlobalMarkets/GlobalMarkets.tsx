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

  const formatLocal = (tz: string | null | undefined) => {
    if (!tz) return '—';
    const now = new Date();
    try {
      return new Intl.DateTimeFormat('en-US', {
        timeZone: tz,
        weekday: 'short',
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

  const activeCount = markets.filter((m: Market) => String(m.status).toUpperCase() === 'OPEN').length;
  const totalCount = markets.length;

  const COUNTRY_BY_KEY: Record<string, string> = {
    tokyo: 'Japan',
    shanghai: 'China',
    bombay: 'India',
    london: 'United Kingdom',
  };

  const countryLabel = (m: Market) => {
    const explicit = (m.country ?? '').trim();
    if (explicit) return explicit;

    const key = (m.key ?? '').trim().toLowerCase();
    if (key && COUNTRY_BY_KEY[key]) return COUNTRY_BY_KEY[key];

    const fallback = (m.display_name ?? m.name ?? '').trim();
    if (!fallback) return '—';
    return fallback
      .replace(/\bstock exchange\b/gi, '')
      .replace(/\bexchange\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

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
            <col className="col-country" />
            <col className="col-local" />
            <col className="col-open" />
            <col className="col-close" />
            <col className="col-status" />
          </colgroup>
          <thead>
            <tr>
              <th>COUNTRY</th>
              <th>LOCAL</th>
              <th>OPEN</th>
              <th>CLOSE</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((market: Market) => {
              const status = String(market.status ?? 'UNKNOWN').toUpperCase();
              const isOpen = status === 'OPEN';
              const statusColor = isOpen ? 'open' : 'closed';
              const title = market.key ? `${market.key} • ${market.timezone_name ?? ''}` : market.timezone_name ?? '';
              const displayName = countryLabel(market);
              return (
                <tr
                  key={market.id ?? market.key ?? displayName}
                  className={statusColor}
                  title={title}
                >
                  <td className="market-name">{displayName}</td>
                  <td className="market-local">{formatLocal(market.timezone_name)}</td>
                  <td className="market-open">{market.market_open_time ?? '—'}</td>
                  <td className="market-close">{market.market_close_time ?? '—'}</td>
                  <td className="market-status">
                    <span className={`status-indicator ${statusColor}`}>{status}</span>
                  </td>
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
