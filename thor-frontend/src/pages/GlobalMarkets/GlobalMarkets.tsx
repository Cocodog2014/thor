import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Market } from '../../types';
import marketsService from '../../services/markets';
import { useGlobalTimer } from '../../context/GlobalTimerContext';
import './GlobalMarkets.css';

const DEFAULT_REFRESH_TICKS = 1; // every second
const MAX_BACKOFF_TICKS = 60; // cap retry window to 60 seconds

const GlobalMarkets: React.FC = () => {
  const { tick, now, marketStatus, statusError } = useGlobalTimer();

  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isStale, setIsStale] = useState(false);
  const [nextFetchTick, setNextFetchTick] = useState(0);

  const backoffRef = useRef(DEFAULT_REFRESH_TICKS);
  const bootstrapRef = useRef(false);

  const fetchMarkets = useCallback(async (reason: 'initial' | 'timer', currentTick: number) => {
    if (!bootstrapRef.current) {
      setLoading(true);
    }

    try {
      console.debug(`[GlobalMarkets] fetching (${reason})`);
      const data = await marketsService.getAll();
      const sortedMarkets = data.results.sort((a, b) => a.sort_order - b.sort_order);
      setMarkets(sortedMarkets);
      setLastUpdate(new Date());
      setError(null);
      setIsStale(false);
      backoffRef.current = DEFAULT_REFRESH_TICKS;
    } catch (err) {
      console.error('[GlobalMarkets] fetch failed, backing off', err);
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_TICKS);
      setError(`Lost connection to global markets (retrying in ${backoffRef.current}s)`);
      setIsStale(true);
    } finally {
      bootstrapRef.current = true;
      setLoading(false);
      setNextFetchTick(currentTick + backoffRef.current);
    }
  }, []);

  useEffect(() => {
    fetchMarkets('initial', 0);
  }, [fetchMarkets]);

  useEffect(() => {
    if (!bootstrapRef.current) return;
    if (tick === 0) return;
    if (tick < nextFetchTick) return;
    fetchMarkets('timer', tick);
  }, [tick, nextFetchTick, fetchMarkets]);

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
    const ms: any = m.market_status;
    const state: string | undefined = ms.current_state;
    const secs: number = (ms.seconds_to_next_event as number | undefined) ?? 0;
    const hours = Math.floor(secs / 3600);

    // When closed and next event is open, show days or countdown
    if ((state === 'CLOSED' || state === 'PREOPEN' || state === 'HOLIDAY_CLOSED') && ms.next_event === 'open') {
      if (hours >= 24) {
        const days = Math.max(1, Math.ceil(secs / 86400));
        return `${days} day${days > 1 ? 's' : ''}`;
      }
      return `${formatHms(secs)}`;
    }

    // Default to scheduled open time
    return m.market_open_time;
  };

  const closeCellText = (m: Market): string => {
    const ms: any = m.market_status;
    const state: string | undefined = ms.current_state;
    const secs: number = (ms.seconds_to_next_event as number | undefined) ?? 0;

    if (isWeekend(m)) return 'WEEKEND';
    if (state === 'HOLIDAY_CLOSED') return 'HOLIDAY';

    if (state === 'OPEN' || state === 'PRECLOSE') {
      return formatHms(secs);
    }
    return m.market_close_time;
  };

  return (
    <div className="timezone-container">
      {error && <div className="error-message">⚠️ {error}</div>}
      {statusError && <div className="error-message">⚠️ {statusError}</div>}
      <div className="markets-table-container">
        <div className="markets-table-header">
          <div className="last-update">
            <span className="live-indicator" title={isStale ? 'Reconnecting…' : 'Live'}>
              {isStale ? '🟡' : '🟢'}
            </span>
            {' '}
            UTC time: {now.toLocaleTimeString('en-US', {
              timeZone: 'UTC',
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            })}
            {' • '}Last update: {lastUpdate.toLocaleTimeString('en-US', {
              timeZone: 'UTC',
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            })}
          </div>
          <div className="markets-table-status">
            {marketStatus ? (
              <>
                <span>
                  Active: {marketStatus.activeMarkets}/{marketStatus.totalMarkets}
                </span>
                {marketStatus.currentlyTrading.length > 0 && (
                  <span className="currently-trading">
                    Trading now: {marketStatus.currentlyTrading.slice(0, 3).join(', ')}
                  </span>
                )}
              </>
            ) : (
              <span>Syncing market status…</span>
            )}
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
            {markets.map((market) => {
              const isOpen = market.market_status.is_in_trading_hours && market.status === 'OPEN';
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
                    <span className={`status-indicator ${statusColor}`}>{isOpen ? 'OPEN' : 'CLOSED'}</span>
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
