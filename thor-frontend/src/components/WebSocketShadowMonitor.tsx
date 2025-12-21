/**
 * Shadow Mode Monitor - WebSocket Testing
 * 
 * Shows phased cutover status:
 * - Green features = using WebSocket
 * - Gray features = still using REST (shadow mode logs)
 */

import { useEffect, useState } from 'react';
import { useWsConnection, useWsMessage } from '../realtime';
import { wssCutover } from '../services/websocket-cutover';

type FeatureStatus = 'ws' | 'rest' | 'both';

export function WebSocketShadowMonitor() {
  const connected = useWsConnection();
  const [messageCount, setMessageCount] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<string>('Never');
  const [featureStatuses, setFeatureStatuses] = useState({
    account_balance: 'rest' as FeatureStatus,
    positions: 'rest' as FeatureStatus,
    intraday: 'rest' as FeatureStatus,
    global_market: 'rest' as FeatureStatus,
  });

  // Initialize feature statuses from cutover manager
  useEffect(() => {
    const flags = wssCutover.getStatus();
    const statuses: Record<keyof typeof featureStatuses, FeatureStatus> = {
      account_balance: 'rest',
      positions: 'rest',
      intraday: 'rest',
      global_market: 'rest',
    };
    
    for (const [feature, isWs] of Object.entries(flags)) {
      statuses[feature as keyof typeof featureStatuses] = isWs ? 'ws' : 'rest';
    }
    
    setFeatureStatuses(statuses);
    console.log(wssCutover.getSummary());
  }, []);

  // Monitor all message types and update count
  useWsMessage('heartbeat', () => {
    setMessageCount((c) => c + 1);
    setLastMessageTime(new Date().toLocaleTimeString());
  });
  useWsMessage('account_balance', () => {});
  useWsMessage('positions', () => {});
  useWsMessage('intraday_bar', () => {});
  useWsMessage('market_status', () => {});
  useWsMessage('vwap_update', () => {});
  useWsMessage('twenty_four_hour', () => {});
  useWsMessage('error_message', () => {});
  useWebSocketMessage('error_message', () => {});

  useEffect(() => {
    if (connected) {
      console.log('🟢 WebSocket shadow mode: CONNECTED');
      return () => {
        console.log('🔴 WebSocket shadow mode: DISCONNECTED');
      };
    }
  }, [connected]);

  const getFeatureColor = (status: FeatureStatus): string => {
    switch (status) {
      case 'ws':
        return '#10b981'; // Green - using WebSocket
      case 'rest':
        return '#9ca3af'; // Gray - using REST (shadow mode)
      case 'both':
        return '#f59e0b'; // Orange - transitioning
      default:
        return '#6b7280';
    }
  };

  const getFeatureLabel = (status: FeatureStatus): string => {
    switch (status) {
      case 'ws':
        return '✅';
      case 'rest':
        return '⚪';
      case 'both':
        return '⚡';
      default:
        return '?';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 10,
        right: 10,
        padding: '12px 16px',
        backgroundColor: '#1f2937',
        color: '#f3f4f6',
        borderRadius: '6px',
        fontSize: '12px',
        fontFamily: 'monospace',
        zIndex: 9999,
        maxWidth: '280px',
        border: `2px solid ${connected ? '#10b981' : '#ef4444'}`,
      }}
      title="WebSocket Cutover Monitor - Check console for message logs"
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        🔌 WS Cutover Status
      </div>
      
      <div style={{ marginBottom: '8px' }}>
        Connection: {connected ? '✅ Connected' : '❌ Disconnected'}
      </div>

      <div style={{ marginBottom: '8px', fontSize: '11px' }}>
        <div style={{ marginBottom: '4px', fontWeight: 'bold', color: '#d1d5db' }}>
          Features:
        </div>
        {Object.entries(featureStatuses).map(([feature, status]) => (
          <div
            key={feature}
            style={{
              marginBottom: '2px',
              paddingLeft: '8px',
              borderLeft: `3px solid ${getFeatureColor(status)}`,
            }}
          >
            {getFeatureLabel(status)} {feature}
          </div>
        ))}
      </div>

      <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '8px' }}>
        Messages: {messageCount} | Last: {lastMessageTime}
      </div>

      <div style={{ fontSize: '9px', color: '#6b7280', marginTop: '6px' }}>
        ✅ = WS | ⚪ = REST | ⚡ = Transitioning
      </div>
    </div>
  );
}
