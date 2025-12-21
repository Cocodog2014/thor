/**
 * Shadow Mode Monitor - WebSocket Testing
 * 
 * Shows phased cutover status:
 * - Green features = using WebSocket
 * - Gray features = still using REST (shadow mode logs)
 */

import { useEffect, useState } from 'react';
import { useWsConnection, useWsMessage } from '../realtime';
import type { WsMessage } from '../realtime/types';

export function WebSocketShadowMonitor() {
  const connected = useWsConnection();
  const [messageCount, setMessageCount] = useState(0);
  const [lastMessageTime, setLastMessageTime] = useState<string>('Never');
  const [lastMessageType, setLastMessageType] = useState<string>('none');

  // Track all messages flowing through the new realtime router
  useWsMessage('all', (msg: WsMessage) => {
    setMessageCount((c) => c + 1);
    setLastMessageTime(new Date().toLocaleTimeString());
    if (msg?.type) setLastMessageType(msg.type);
  });

  useEffect(() => {
    if (connected) {
      console.log('🟢 WebSocket monitor: CONNECTED');
      return () => {
        console.log('🔴 WebSocket monitor: DISCONNECTED');
      };
    }
  }, [connected]);

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
        maxWidth: '260px',
        border: `2px solid ${connected ? '#10b981' : '#ef4444'}`,
      }}
      title="WebSocket monitor - logs basic realtime stats"
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        🔌 WS Monitor
      </div>

      <div style={{ marginBottom: '6px' }}>
        Connection: {connected ? '✅ Connected' : '❌ Disconnected'}
      </div>

      <div style={{ fontSize: '10px', color: '#d1d5db', marginBottom: '4px' }}>
        Messages: {messageCount}
      </div>

      <div style={{ fontSize: '10px', color: '#9ca3af' }}>
        Last: {lastMessageTime} ({lastMessageType})
      </div>
    </div>
  );
}
