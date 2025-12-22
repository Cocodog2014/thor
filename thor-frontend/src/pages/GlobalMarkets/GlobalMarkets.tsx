import React from 'react';
import type { Market } from '../../types';
import { useGlobalMarkets } from '../../features/globalMarkets/useGlobalMarkets';
import './GlobalMarkets.css';

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

  const formatHms = (totalSeconds: number) => {
    const s = Math.max(0, totalSeconds);
    const hours = Math.floor(s / 3600);
    const minutes = Math.floor((s % 3600) / 60);
    const seconds = s % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const isWeekend = (m: Market) => m.current_time.day === 'Sat' || m.current_time.day === 'Sun';

  const openCellText = (m: Market): string => {
    const ms = m.market_status ?? { next_event: 'open', seconds_to_next_event: 0 };
    const secs: number = (ms.seconds_to_next_event as number | undefined) ?? 0;
    const hours = Math.floor(secs / 3600);

    if (ms.next_event === 'open' && secs > 0) {
      if (hours >= 24) {
        const days = Math.max(1, Math.ceil(secs / 86400));
        return `${days} day${days > 1 ? 's' : ''}`;
      }
      return formatHms(secs);
    }

    return m.market_open_time;
  };

  const closeCellText = (m: Market): string => {
    const state: string | undefined = m.market_status?.current_state;
    if (isWeekend(m)) return 'WEEKEND';
    if (state === 'HOLIDAY_CLOSED') return 'HOLIDAY';
    return m.market_close_time;
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

  const activeCount = markets.filter((m) => m.market_status?.current_state === 'OPEN').length;
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
            <col className="col-year" />
            <col className="col-month" />
            <col className="col-date" />
            <col className="col-day" />
            <col className="col-open" />
            <col className="col-close" />
            <col className="col-time" />
            <col className="col-status" />
          </colgroup>
          <thead>
            <tr>
              <th>MARKET</th>
              <th>YEAR</th>
              <th>MONTH</th>
              <th>DATE</th>
              <th>DAY</th>
              <th>OPEN</th>
              <th>CLOSE</th>
              <th>CURRENT TIME</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {markets
              .filter((market) => market.market_status && market.current_time)
              .map((market) => {
              const state = market.market_status?.current_state ?? 'UNKNOWN';
              const isOpen = state === 'OPEN' || state === 'PRECLOSE';
              const statusColor = isOpen ? 'open' : 'closed';
              
              return (
                <tr
                  key={market.id}
                  className={statusColor}
                  title={`${market.display_name} - ${market.timezone_name} (${market.currency})`}
                >
                  <td className="market-name">{market.display_name}</td>
                  <td className="market-year">{market.current_time.year}</td>
                  <td className="market-month">{market.current_time.month}</td>
                  <td className="market-date">{market.current_time.date}</td>
                  <td className="market-day">{market.current_time.day}</td>
                  <td className="market-open">{openCellText(market)}</td>
                  <td className="market-close">{closeCellText(market)}</td>
                  <td className="market-time">{market.current_time.formatted_24h}</td>
                  <td className="market-status">
                    <span className={`status-indicator ${statusColor}`}>{state ?? 'UNKNOWN'}</span>
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
