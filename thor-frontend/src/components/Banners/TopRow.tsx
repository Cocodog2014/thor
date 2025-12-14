// TopRow.tsx
import React, { useMemo, useState } from 'react';
import type { AccountSummary } from './bannerTypes';
import BrokersAccountModal from '../modals/BrokersAccount/BrokersAccountModal';
import api from '../../services/api';

interface TopRowProps {
  isConnected: boolean;
  connectionLabel: string;
  connectionDetails: string;
  accounts: AccountSummary[];
  selectedAccountId: number | null;
  onAccountChange: (id: number) => void;
  onNavigate: (path: string) => void;
}

const TopRow: React.FC<TopRowProps> = ({
  isConnected,
  connectionLabel,
  connectionDetails,
  accounts,
  selectedAccountId,
  onAccountChange,
  onNavigate,
}) => {
  const [showPaperGuard, setShowPaperGuard] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const selectedAccount = useMemo(() => {
    if (!accounts.length) {
      return null;
    }
    if (selectedAccountId === null) {
      return accounts[0];
    }
    return accounts.find((acct) => acct.id === selectedAccountId) ?? accounts[0];
  }, [accounts, selectedAccountId]);

  const brokerLabel = (selectedAccount?.broker ?? '').toLowerCase();
  const isPaperAccount = brokerLabel === 'paper';
  const isApproved = Boolean(selectedAccount?.ok_to_trade);

  const statusLabel = (() => {
    if (!selectedAccount) {
      return 'No accounts available';
    }
    if (isPaperAccount) {
      return 'Mode: Paper';
    }
    if (!isApproved) {
      return 'Needs setup';
    }
    const brokerName = selectedAccount.display_name || selectedAccount.broker || 'Brokerage';
    return `Live: ${brokerName}`;
  })();

  const statusVariant = !selectedAccount
    ? 'warning'
    : isPaperAccount
    ? 'paper'
    : isApproved
    ? 'live'
    : 'warning';

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
              onChange={(e) => onAccountChange(Number(e.target.value))}
            >
              {accounts.map((acct) => (
                <option key={acct.id} value={acct.id}>
                  {acct.broker_account_id}
                  {acct.display_name ? ` (${acct.display_name})` : ''}
                </option>
              ))}
            </select>
            <span className={`account-mode-pill ${statusVariant}`}>{statusLabel}</span>
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
        <button
          className="home-quick-link"
          type="button"
          onClick={launchSchwabConnect}
        >
          <span>⚙️</span>Setup Brokerage Account
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
