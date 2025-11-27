import React, { useState, useEffect } from 'react';
import type { Market } from '../../types';
import marketsService from '../../services/markets';

const GlobalMarkets: React.FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Fetch markets from backend API
  useEffect(() => {
    const fetchMarkets = async () => {
      try {
        const data = await marketsService.getAll();
        const sortedMarkets = data.results.sort((a, b) => a.sort_order - b.sort_order);
        setMarkets(sortedMarkets);
        setLastUpdate(new Date());
        setError(null);
      } catch (err) {
        console.error('Error fetching markets:', err);
        setError('Failed to load market data. Please check if the backend is running.');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchMarkets();

    // Update every 1 seconds to get fresh data from backend (live updating)
    const interval = setInterval(fetchMarkets, 1000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="timezone-container">
        <div className="markets-table-container">
          <div className="markets-table-header">
            <h2>🌍 Global Markets</h2>
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
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {/* Table layout with all market data columns */}
      <div className="markets-table-container">
        <div className="markets-table-header">
          <h2>🌍 Global Markets</h2>
          <div className="last-update">
            <span className="live-indicator">🟢</span>
            UTC time: {lastUpdate.toLocaleTimeString('en-US', { 
              timeZone: 'UTC',
              hour12: false,
              hour: '2-digit',
              minute: '2-digit', 
              second: '2-digit'
            })}
          </div>
        </div>
        <table className="markets-table">
          {/* Define proportional column widths for better readability */}
          <colgroup>
            <col className="col-market" /> {/* MARKET */}
            <col className="col-year" />  {/* YEAR */}
            <col className="col-month" />  {/* MONTH */}
            <col className="col-date" />  {/* DATE */}
            <col className="col-day" /> {/* DAY */}
            <col className="col-open" /> {/* OPEN */}
            <col className="col-close" /> {/* CLOSE */}
            <col className="col-time" /> {/* CURRENT TIME */}
            <col className="col-status" /> {/* STATUS */}
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
                  <td className="market-name">
                    {market.display_name}
                  </td>
                  <td className="market-year">
                    {market.current_time.year}
                  </td>
                  <td className="market-month">
                    {market.current_time.month}
                  </td>
                  <td className="market-date">
                    {market.current_time.date}
                  </td>
                  <td className="market-day">
                    {market.current_time.day}
                  </td>
                  <td className="market-open">
                    {openCellText(market)}
                  </td>
                  <td className="market-close">
                    {closeCellText(market)}
                  </td>
                  <td className="market-time">
                    {market.current_time.formatted_24h}
                  </td>
                  <td className="market-status">
                    <span className={`status-indicator ${statusColor}`}>
                      {isOpen ? 'OPEN' : 'CLOSED'}
                    </span>
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
