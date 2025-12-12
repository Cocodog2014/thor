// TopRow.tsx
import React from 'react';
import type { AccountSummary } from './bannerTypes';

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
  return (
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
        ) : (
          <span className="home-account-id">No accounts</span>
        )}
        <button
          className="home-quick-link"
          type="button"
          onClick={() => onNavigate('/app/user/brokers')}
          style={{ marginLeft: 8 }}
        >
          <span>🔌</span>Connect Broker Account
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
          onClick={() => onNavigate('/app/user/brokers')}
        >
          <span>⚙️</span>Setup
        </button>
      </div>
    </div>
  );
};

export default TopRow;
