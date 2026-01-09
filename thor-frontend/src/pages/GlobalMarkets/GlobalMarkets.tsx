import React, { useEffect, useState } from 'react';
import { useGlobalMarkets } from '../../features/globalMarkets/useGlobalMarkets';
import './GlobalMarkets.css';

import type { Market } from '../../types';

const GlobalMarkets: React.FC = () => {
  const { markets, loading, error, lastUpdate, isStale } = useGlobalMarkets();
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

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

  const formatLocal = (tz: string | null | undefined, when: Date) => {
    if (!tz) return '—';
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
      }).format(when);
    } catch {
      return '—';
    }
  };

  const isWeekendInTz = (tz: string | null | undefined, when: Date) => {
    if (!tz) return false;
    try {
      const weekday = new Intl.DateTimeFormat('en-US', { timeZone: tz, weekday: 'short' }).format(when);
      return weekday === 'Sat' || weekday === 'Sun';
    } catch {
      return false;
    }
  };

  const formatCountdown = (targetIso: string | null | undefined, when: Date) => {
    if (!targetIso) return null;
    const target = new Date(targetIso);
    if (Number.isNaN(target.getTime())) return null;

    const ms = target.getTime() - when.getTime();
    if (ms <= 0) return null;

    const totalSeconds = Math.floor(ms / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const hh = String(hours).padStart(2, '0');
    const mm = String(minutes).padStart(2, '0');
    const ss = String(seconds).padStart(2, '0');
    return days > 0 ? `${days}d ${hh}:${mm}:${ss}` : `${hh}:${mm}:${ss}`;
  };

  const openCell = (m: Market, when: Date) => {
    if (isWeekendInTz(m.timezone_name, when)) return 'Weekend';

    const status = String(m.status ?? '').toUpperCase();
    if (status === 'OPEN') return m.market_open_time ?? '—';

    const countdown = formatCountdown(m.next_transition_utc, when);
    return countdown ? `Opens in ${countdown}` : (m.market_open_time ?? '—');
  };

  const closeCell = (m: Market, when: Date) => {
    if (isWeekendInTz(m.timezone_name, when)) return 'Weekend';

    const status = String(m.status ?? '').toUpperCase();
    if (status !== 'OPEN') return m.market_close_time ?? '—';

    const countdown = formatCountdown(m.next_transition_utc, when);
    return countdown ? `Closes in ${countdown}` : (m.market_close_time ?? '—');
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
            UTC time: {formatUtcTime(now)}
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
                  <td className="market-local">{formatLocal(market.timezone_name, now)}</td>
                  <td className="market-open">{openCell(market, now)}</td>
                  <td className="market-close">{closeCell(market, now)}</td>
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
