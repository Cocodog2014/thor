/**
 * Shadow Mode Monitor - WebSocket Testing
 * 
 * Logs all WebSocket messages to console without affecting production data.
 * Keep REST endpoints active, just listen to WebSocket in parallel.
 */

import { useEffect, useState } from 'react';
import { useWebSocketConnection, useWebSocketMessage } from '../hooks/useWebSocket';

export function WebSocketShadowMonitor() {
  const connected = useWebSocketConnection();
  const [messageCount, setMessageCount] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<string>('Never');

  // Monitor heartbeat messages
  useWebSocketMessage('heartbeat', () => {
    setMessageCount((c) => c + 1);
    setLastMessageTime(new Date().toLocaleTimeString());
  });

  // Monitor market status (log only, no state update)
  useWebSocketMessage('market_status', () => {});

  // Monitor intraday bars (log only, no state update)
  useWebSocketMessage('intraday_bar', () => {});

  // Monitor quotes (log only, no state update)
  useWebSocketMessage('quote_tick', () => {});

  // Monitor VWAP (log only, no state update)
  useWebSocketMessage('vwap_update', () => {});

  // Monitor 24h updates (log only, no state update)
  useWebSocketMessage('twenty_four_hour', () => {});

  // Monitor errors
  useWebSocketMessage('error_message', () => {});

  useEffect(() => {
    if (connected) {
      console.log('🟢 WebSocket shadow mode: CONNECTED');
      return () => {
        console.log('🔴 WebSocket shadow mode: DISCONNECTED');
      };
    }
  }, [connected]);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 10,
        right: 10,
        padding: '10px 15px',
        backgroundColor: connected ? '#10b981' : '#ef4444',
        color: 'white',
        borderRadius: '4px',
        fontSize: '12px',
        fontFamily: 'monospace',
        zIndex: 9999,
        maxWidth: '250px',
      }}
      title="WebSocket Shadow Mode Monitor - Check console for message logs"
    >
      <div style={{ fontWeight: 'bold' }}>🔌 WS Shadow Mode</div>
      <div>Status: {connected ? '✅ Connected' : '❌ Disconnected'}</div>
      <div>Messages: {messageCount}</div>
      <div>Last: {lastMessageTime}</div>
      <div style={{ fontSize: '10px', marginTop: '5px', opacity: 0.8 }}>
        Open DevTools (F12) → Console to see message logs
      </div>
    </div>
  );
}
