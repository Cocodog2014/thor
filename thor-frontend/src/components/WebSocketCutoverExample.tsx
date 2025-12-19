/**
 * Example Component: Using WebSocket-Aware Hooks During Cutover
 * 
 * This shows how to switch between REST and WebSocket seamlessly
 * as each feature is cut over. Use this pattern in your components.
 */

import { useEffect, useState } from 'react';
import { useWebSocketEnabled, useWebSocketFeatureData, getDataSource } from '../hooks/useWebSocketAware';

interface AccountBalance {
  cash: number;
  portfolio_value: number;
  buying_power: number;
  timestamp: string;
}

/**
 * Example: AccountBalance component that supports both REST and WebSocket
 * 
 * During cutover:
 * - Before: Fetches from REST endpoint
 * - During Shadow Mode: Fetches from REST + logs WebSocket messages
 * - After: Uses WebSocket only
 */
export function AccountBalanceExample() {
  const [balance, setBalance] = useState<AccountBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const wsEnabled = useWebSocketEnabled('account_balance');
  const dataSource = getDataSource('account_balance');

  // Set up WebSocket listener (only if enabled)
  useWebSocketFeatureData('account_balance', 'account_balance', (data: AccountBalance) => {
    console.log('📡 Account Balance from WebSocket:', data);
    setBalance(data);
  });

  // During shadow mode, also fetch from REST
  useEffect(() => {
    if (!wsEnabled) {
      // Still using REST
      fetchBalance();
    }
  }, [wsEnabled]);

  const fetchBalance = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/account/balance/');
      if (response.ok) {
        const data = await response.json();
        setBalance(data);
      }
    } catch (error) {
      console.error('Error fetching balance:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !balance) {
    return <div>Loading balance...</div>;
  }

  return (
    <div style={{ padding: '10px', border: '1px solid #ccc' }}>
      <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
        📊 Data Source: {dataSource}
        {wsEnabled && ' ✅'}
      </div>
      {balance && (
        <div>
          <div>Cash: ${balance.cash.toFixed(2)}</div>
          <div>Portfolio: ${balance.portfolio_value.toFixed(2)}</div>
          <div>Buying Power: ${balance.buying_power.toFixed(2)}</div>
          <div style={{ fontSize: '11px', color: '#999' }}>
            Last: {new Date(balance.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Example: Positions component (similar pattern)
 */
export function PositionsExample() {
  const [positions, setPositions] = useState<Array<{ symbol: string; quantity: number; price: number; }>>([]);
  const wsEnabled = useWebSocketEnabled('positions');
  const dataSource = getDataSource('positions');

  // Listen to WebSocket if enabled
  useWebSocketFeatureData('positions', 'positions', (data) => {
    console.log('📡 Positions from WebSocket:', data);
    setPositions(data.positions || []);
  });

  // Shadow mode: fetch from REST
  useEffect(() => {
    if (!wsEnabled) {
      fetchPositions();
    }
  }, [wsEnabled]);

  const fetchPositions = async () => {
    try {
      const response = await fetch('/api/positions/');
      if (response.ok) {
        const data = await response.json();
        setPositions(data.positions || []);
      }
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  return (
    <div style={{ padding: '10px', border: '1px solid #ccc' }}>
      <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
        📈 Data Source: {dataSource}
        {wsEnabled && ' ✅'}
      </div>
      <div>Total Positions: {positions.length}</div>
      {positions.map((pos) => (
        <div key={pos.symbol} style={{ paddingLeft: '10px', fontSize: '12px' }}>
          {pos.symbol}: {pos.quantity} @ ${pos.price?.toFixed(2) || 'N/A'}
        </div>
      ))}
    </div>
  );
}

/**
 * Example: Dashboard showing cutover status
 */
export function CutoverStatusExample() {
  const accountBalanceWs = useWebSocketEnabled('account_balance');
  const positionsWs = useWebSocketEnabled('positions');
  const intradayWs = useWebSocketEnabled('intraday');
  const globalMarketWs = useWebSocketEnabled('global_market');

  const features = [
    { name: 'Account Balance', enabled: accountBalanceWs },
    { name: 'Positions', enabled: positionsWs },
    { name: 'Intraday', enabled: intradayWs },
    { name: 'Global Market', enabled: globalMarketWs },
  ];

  const totalEnabled = features.filter((f) => f.enabled).length;
  const allCutover = totalEnabled === features.length;

  return (
    <div style={{ padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
      <h3>🔌 WebSocket Cutover Status</h3>
      <div style={{ marginBottom: '10px' }}>
        {allCutover ? '✅ FULL CUTOVER' : `⚡ PARTIAL: ${totalEnabled}/${features.length} features`}
      </div>
      {features.map((feature) => (
        <div
          key={feature.name}
          style={{
            padding: '8px',
            marginBottom: '5px',
            backgroundColor: feature.enabled ? '#d4edda' : '#e7e7e7',
            borderRadius: '3px',
            fontSize: '12px',
          }}
        >
          {feature.enabled ? '✅ WS' : '⚪ REST'} {feature.name}
        </div>
      ))}
    </div>
  );
}

/**
 * USAGE PATTERN:
 * 
 * 1. During Shadow Mode (all features disabled):
 *    - REST endpoints still return data
 *    - WebSocket messages logged to console
 *    - UI shows "⚪ REST (Shadow)"
 * 
 * 2. Enable Account Balance feature:
 *    - export WS_FEATURE_ACCOUNT_BALANCE=true
 *    - Restart server
 *    - Component switches to WebSocket automatically
 *    - UI shows "✅ WebSocket"
 * 
 * 3. Repeat for other features one at a time
 *    - Positions
 *    - Intraday
 *    - Global Market
 * 
 * 4. Once verified, delete REST timer:
 *    - Remove from stack_start.py registry
 *    - Delete REST endpoint from views.py
 *    - Commit changes
 * 
 * 5. Repeat for each feature
 * 
 * FALLBACK:
 * If WebSocket fails:
 *   - Set feature flag to false
 *   - Component falls back to REST
 *   - Zero downtime
 */
