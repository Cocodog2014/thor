// TopRow.tsx
import React, { useMemo, useState } from 'react';
import type { AccountSummary, SchwabHealth } from './bannerTypes';
import BrokersAccountModal from '../modals/BrokersAccount/BrokersAccountModal';
import api from '../../services/api';

interface TopRowProps {
  isConnected: boolean;
  connectionLabel: string;
  connectionDetails: string;
  accounts: AccountSummary[];
  selectedAccountId: string | null;
  onAccountChange: (id: string | null) => void;
  onNavigate: (path: string) => void;
  schwabHealth?: SchwabHealth | null;
}

const TopRow: React.FC<TopRowProps> = ({
  isConnected,
  connectionLabel,
  connectionDetails,
  accounts,
  selectedAccountId,
  onAccountChange,
  onNavigate,
  schwabHealth,
}) => {
  const [showPaperGuard, setShowPaperGuard] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const formatDuration = (totalSeconds?: number | null) => {
    if (totalSeconds === undefined || totalSeconds === null) {
      return null;
    }
    if (totalSeconds <= 0) {
      return 'expires soon';
    }
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m left`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds}s left`;
    }
    return `${seconds}s left`;
  };

  const selectedAccount = useMemo(
    () => accounts.find((acct) => acct.broker_account_id === selectedAccountId) ?? null,
    [accounts, selectedAccountId],
  );

  const brokerLabel = (selectedAccount?.broker ?? '').toLowerCase();
  const isPaperAccount = brokerLabel === 'paper';
  const isApproved = Boolean(selectedAccount?.ok_to_trade);

  const { statusLabel, statusVariant, statusMeta } = (() => {
    if (!selectedAccount) {
      return { statusLabel: 'No accounts available', statusVariant: 'warning', statusMeta: null } as const;
    }
    if (isPaperAccount) {
      return { statusLabel: 'Mode: Paper', statusVariant: 'paper', statusMeta: null } as const;
    }
    if (!isApproved) {
      return { statusLabel: 'Needs setup', statusVariant: 'warning', statusMeta: 'Complete broker setup to trade' } as const;
    }

    if (!schwabHealth) {
      return { statusLabel: 'Checking Schwab…', statusVariant: 'paper', statusMeta: null } as const;
    }

    if (!schwabHealth.connected) {
      const meta = schwabHealth.approval_state === 'not_connected'
        ? 'Connect Schwab to enable balances'
        : schwabHealth.last_error || 'Awaiting Schwab approval';
      return { statusLabel: 'Schwab: Not connected', statusVariant: 'warning', statusMeta: meta } as const;
    }

    if (schwabHealth.token_expired) {
      return { statusLabel: 'Schwab: Token expired', statusVariant: 'warning', statusMeta: 'Refresh OAuth to continue streaming' } as const;
    }

    const brokerName = selectedAccount.display_name || selectedAccount.broker || 'Schwab';
    const approval = schwabHealth.approval_state === 'trading_enabled' ? 'Trading enabled' : 'Read-only';
    const expiry = formatDuration(schwabHealth.seconds_until_expiry);
    const metaParts = [approval, expiry].filter(Boolean);
    return { statusLabel: `Live: ${brokerName}`, statusVariant: 'live', statusMeta: metaParts.join(' • ') || null } as const;
  })();

  const launchSchwabConnect = async () => {
    try {
      setConnectError(null);
      const { data } = await api.get('schwab/oauth/start/');
      const authUrl = data?.auth_url;
      if (!authUrl) {
        setConnectError('Unable to start Schwab OAuth (missing URL).');
        return;
      }
      window.location.href = authUrl;
    } catch (error) {
      console.error('GlobalBanner: failed to start Schwab OAuth', error);
      setConnectError('Unable to reach Schwab. Try again or visit Broker Connections.');
    }
  };

  const handleStartBrokerageAccount = () => {
    if (!selectedAccount || isPaperAccount) {
      setShowPaperGuard(true);
      return;
    }

    launchSchwabConnect();
  };

  const handleCloseModal = () => setShowPaperGuard(false);
  const handleGoToSetup = () => {
    setShowPaperGuard(false);
    onNavigate('/app/user/brokers');
  };

  return (
    <>
      <div className="global-banner-row global-banner-row-top">
      <div className="global-banner-left">
        <span
          className={`home-connection ${
            isConnected ? 'connected' : 'disconnected'
          }`}
        >
          <span
            className={`home-connection-dot ${
              isConnected ? 'connected' : 'disconnected'
            }`}
          />
          {connectionLabel}
        </span>
        <span
          className={`home-connection-details ${
            isConnected ? '' : 'offline'
          }`}
        >
          {connectionDetails}
        </span>

        {/* Account dropdown replaces hard-coded account id */}
        {accounts.length > 0 ? (
          <>
            <select
              className="home-account-select"
              aria-label="Select trading account"
              value={selectedAccountId ?? ''}
              onChange={(e) => onAccountChange(e.target.value || null)}
            >
              {accounts.map((acct) => (
                <option key={acct.broker_account_id} value={acct.broker_account_id}>
                  {acct.account_number || acct.broker_account_id}
                  {acct.display_name ? ` (${acct.display_name})` : ''}
                </option>
              ))}
            </select>
            <span className={`account-mode-pill ${statusVariant}`}>{statusLabel}</span>
            {statusMeta && (
              <span className="schwab-health-meta">{statusMeta}</span>
            )}
          </>
        ) : (
          <span className="home-account-id">No accounts</span>
        )}
        <button
          className="home-quick-link"
          type="button"
          onClick={handleStartBrokerageAccount}
          style={{ marginLeft: 8 }}
        >
          <span>🚀</span>Start Brokerage Account
        </button>
      </div>

      <div className="global-banner-right">
        <a href="mailto:admin@360edu.org" className="home-contact-link">
          <span>📧</span> admin@360edu.org
        </a>
        <button
          className="home-quick-link"
          type="button"
          onClick={() => onNavigate('/app/home')}
        >
          <span>🏠</span>Home
        </button>
        <button className="home-quick-link" type="button">
          <span>💬</span>Messages
        </button>
        <button className="home-quick-link" type="button">
          <span>🛟</span>Support
        </button>
        <button className="home-quick-link" type="button">
          <span>💭</span>Chat Rooms
        </button>
        {connectError && (
          <span className="home-banner-error" role="status">
            {connectError}
          </span>
        )}
      </div>
      </div>

      <BrokersAccountModal
        open={showPaperGuard}
        onClose={handleCloseModal}
        onGoToSetup={handleGoToSetup}
      />
    </>
  );
};

export default TopRow;
