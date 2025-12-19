/**
 * Gradual WebSocket Cutover Manager
 * 
 * Per-feature cutover: use WebSocket if enabled, fall back to REST.
 * Environment variables control which features are live.
 */

type FeatureFlag = 'account_balance' | 'positions' | 'intraday' | 'global_market';

export class WebSocketCutoverManager {
  private featureFlags: Record<FeatureFlag, boolean> = {
    account_balance: import.meta.env.VITE_WS_FEATURE_ACCOUNT_BALANCE === 'true',
    positions: import.meta.env.VITE_WS_FEATURE_POSITIONS === 'true',
    intraday: import.meta.env.VITE_WS_FEATURE_INTRADAY === 'true',
    global_market: import.meta.env.VITE_WS_FEATURE_GLOBAL_MARKET === 'true',
  };

  /**
   * Check if a feature should use WebSocket
   */
  isWebSocketEnabled(feature: FeatureFlag): boolean {
    return this.featureFlags[feature];
  }

  /**
   * Get all feature statuses
   */
  getStatus(): Record<FeatureFlag, boolean> {
    return { ...this.featureFlags };
  }

  /**
   * Check if all features are using WebSocket
   */
  isFullyCutover(): boolean {
    return Object.values(this.featureFlags).every(Boolean);
  }

  /**
   * Check if any feature is using WebSocket
   */
  isPartiallyCutover(): boolean {
    return Object.values(this.featureFlags).some(Boolean);
  }

  /**
   * Get cutover status summary for logging
   */
  getSummary(): string {
    const enabled = Object.entries(this.featureFlags)
      .filter(([, enabled]) => enabled)
      .map(([name]) => name);
    const disabled = Object.entries(this.featureFlags)
      .filter(([, enabled]) => !enabled)
      .map(([name]) => name);

    let summary = '🔌 WebSocket Cutover Status:\n';
    if (enabled.length > 0) {
      summary += `  ✅ Live (WS): ${enabled.join(', ')}\n`;
    }
    if (disabled.length > 0) {
      summary += `  ⚪ Shadow (REST): ${disabled.join(', ')}\n`;
    }
    return summary;
  }
}

export const wssCutover = new WebSocketCutoverManager();
