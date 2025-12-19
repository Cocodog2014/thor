/**
 * useWebSocketAware - Route data requests between REST and WebSocket
 * 
 * During cutover, some features may use WebSocket while others still use REST.
 * This hook helps components switch seamlessly based on feature flags.
 */

import { wssCutover } from '../services/websocket-cutover';
import { useWebSocketMessage } from './useWebSocket';

export type WebSocketFeature = 'account_balance' | 'positions' | 'intraday' | 'global_market';

/**
 * Check if a feature is currently using WebSocket
 * @param feature - Feature to check
 * @returns true if using WebSocket, false if still using REST (shadow mode)
 */
export function useWebSocketEnabled(feature: WebSocketFeature): boolean {
  return wssCutover.isWebSocketEnabled(feature);
}

/**
 * Get the source string for UI display
 * @param feature - Feature to check
 * @returns 'WebSocket' or 'REST (Shadow)'
 */
export function getDataSource(feature: WebSocketFeature): string {
  return wssCutover.isWebSocketEnabled(feature) ? 'WebSocket' : 'REST (Shadow)';
}

/**
 * Hook to listen to WebSocket message for a feature (if enabled)
 * Falls back to undefined if WebSocket not enabled for this feature
 */
export function useWebSocketFeatureData<T>(
  feature: WebSocketFeature,
  messageType: string,
  handler: (data: T) => void,
  enabled: boolean = true
) {
  const wsEnabled = useWebSocketEnabled(feature);

  // Only set up listener if both the feature AND hook are enabled
  useWebSocketMessage(messageType, handler, wsEnabled && enabled, true);

  return wsEnabled;
}

/**
 * Log cutover status on mount
 */
export function useCutoverStatus() {
  const status = wssCutover.getStatus();
  const summary = wssCutover.getSummary();
  
  return {
    status,
    summary,
    isFullyCutover: wssCutover.isFullyCutover(),
    isPartiallyCutover: wssCutover.isPartiallyCutover(),
  };
}
