import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';
import api from '../../services/api';

// Shape of the account summary coming from /api/actandpos/accounts
interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string;
  currency: string;
  net_liq: string;
  cash: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}

// Permanent banner under the AppBar, shows connection/account info + balances + tabs.
const GlobalBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [connectionStatus, setConnectionStatus] =
    useState<'connected' | 'disconnected'>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  // Accounts + selected account for the dropdown
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);

  // Helper to format currency-like strings safely
  const formatCurrency = (value?: string | null) => {
    if (value === null || value === undefined) return '—';
    const num = Number(value);
    if (Number.isNaN(num)) return value ?? '—';
    return num.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  // Ping the quotes API to determine "Connected / Disconnected" + last update time
  useEffect(() => {
    let isMounted = true;

    const checkConnection = async () => {
      try {
        const { data } = await api.get<{ rows?: unknown[] }>('/quotes/latest', {
          headers: { 'Cache-Control': 'no-store' },
        });
        const rows = Array.isArray(data?.rows) ? data.rows : [];
        const hasLiveData = rows.length > 0;

        if (!isMounted) {
          return;
        }

        if (hasLiveData) {
          setConnectionStatus('connected');
          setLastUpdate(new Date().toLocaleTimeString());
        } else {
          setConnectionStatus('disconnected');
        }
      } catch {
        if (!isMounted) {
          return;
        }
        setConnectionStatus('disconnected');
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Load all accounts for the account selector in the banner
  useEffect(() => {
    let isMounted = true;

    const loadAccounts = async () => {
      try {
        const { data } = await api.get<AccountSummary[]>('/actandpos/accounts', {
          headers: { 'Cache-Control': 'no-store' },
        });
        const accountList = Array.isArray(data) ? data : [];
        if (!isMounted) return;

        setAccounts(accountList);

        // Default to the first account if none selected yet
        if (accountList.length > 0) {
          setSelectedAccountId((prev) => (prev === null ? accountList[0].id : prev));
        }
      } catch (error) {
        if (!isMounted) return;
        console.error('Failed to load accounts list', error);
        setAccounts([]);
      }
    };

    loadAccounts();

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedAccount =
    (selectedAccountId !== null
      ? accounts.find((a) => a.id === selectedAccountId)
      : accounts[0]) || null;

  const isConnected = connectionStatus === 'connected';
  const connectionLabel = isConnected ? 'Connected' : 'Disconnected';
  const connectionDetails = isConnected
    ? lastUpdate
      ? `Realtime data · ${lastUpdate}`
      : 'Realtime data'
    : 'Waiting for live feed';

  // Parent (top) tabs
  const parentTabs: { label: string; path: string; key: string }[] = [
    { label: 'Home', path: '/app/home', key: 'home' },
    { label: 'Trade', path: '/app/trade', key: 'trade' },
    { label: 'Futures', path: '/app/futures', key: 'futures' },
    { label: 'Global', path: '/app/global', key: 'global' },
  ];

  // Child tabs for each parent (generic placeholders for now)
  const childTabsByParent: Record<string, { label: string; path: string }[]> = {
    home: [
      { label: 'Activity & Positions', path: '/app/activity' },
      { label: 'View 2', path: '/app/home' },
      { label: 'View 3', path: '/app/home' },
    ],
    futures: [
      { label: 'Option A', path: '/app/futures' },
      { label: 'Option B', path: '/app/futures' },
      { label: 'Option C', path: '/app/futures' },
    ],
    global: [
      { label: 'Tab 1', path: '/app/global' },
      { label: 'Tab 2', path: '/app/global' },
    ],
    trade: [],
  };

  // Helper to derive parent key from current location
  const deriveParentKey = (pathname: string) =>
    parentTabs.find((tab) => pathname.startsWith(tab.path))?.key ??
    parentTabs[0].key;

  const [activeParentKey, setActiveParentKey] = useState<string>(() =>
    deriveParentKey(location.pathname),
  );
  const ignorePathSyncRef = useRef(false);

  useEffect(() => {
    if (ignorePathSyncRef.current) {
      ignorePathSyncRef.current = false;
      return;
    }

    const derivedKey = deriveParentKey(location.pathname);
    if (derivedKey !== activeParentKey) {
      setActiveParentKey(derivedKey);
    }
  }, [location.pathname, activeParentKey]);

  const handleParentClick = (tabKey: string, tabPath: string) => {
    ignorePathSyncRef.current = true;
    setActiveParentKey(tabKey);
    navigate(tabPath);
  };

  const handleChildClick = (parentKey: string, path: string) => {
    ignorePathSyncRef.current = true;
    setActiveParentKey(parentKey);
    navigate(path);
  };

  const childTabs = childTabsByParent[activeParentKey] ?? [];

  return (
    <div
      className="global-banner"
      role="navigation"
      aria-label="Primary navigation banner"
    >
      {/* Row 1 */}
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
              value={selectedAccount ? selectedAccount.id : ''}
              onChange={(e) => setSelectedAccountId(Number(e.target.value))}
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
        </div>

        <div className="global-banner-right">
          <a href="mailto:admin@360edu.org" className="home-contact-link">
            <span>📧</span> admin@360edu.org
          </a>
          <button
            className="home-quick-link"
            type="button"
            onClick={() => navigate('/app/home')}
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
          <button className="home-quick-link" type="button">
            <span>⚙️</span>Setup
          </button>
        </div>
      </div>

      {/* Row 2 balances – driven by selected account */}
      <div className="global-banner-balances home-balances">
        <span>
          Option Buying Power:
          <span className="home-balance-value">
            {selectedAccount
              ? `$${formatCurrency(selectedAccount.option_buying_power)}`
              : '—'}
          </span>
        </span>
        <span>
          Stock Buying Power:
          <span className="home-balance-value">
            {selectedAccount
              ? `$${formatCurrency(selectedAccount.stock_buying_power)}`
              : '—'}
          </span>
        </span>
        <span>
          Net Liq:
          <span className="home-balance-value">
            {selectedAccount
              ? `$${formatCurrency(selectedAccount.net_liq)}`
              : '—'}
          </span>
        </span>
      </div>

      {/* Row 3 parent tabs */}
      <nav className="global-banner-tabs home-nav">
        {parentTabs.map((tab) => {
          const active = activeParentKey === tab.key;
          return (
            <button
              key={tab.label}
              type="button"
              onClick={() => handleParentClick(tab.key, tab.path)}
              className={`home-nav-button${active ? ' active' : ''}`}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Row 4 child tabs (generic placeholders, not wired yet) */}
      {childTabs.length > 0 && (
        <nav className="global-banner-subtabs">
          {childTabs.map((child) => {
            const active = location.pathname === child.path;
            return (
              <button
                key={child.label}
                type="button"
                onClick={() => handleChildClick(activeParentKey, child.path)}
                className={`home-nav-button-child${active ? ' active' : ''}`}
              >
                {child.label}
              </button>
            );
          })}
        </nav>
      )}
    </div>
  );
};

export default GlobalBanner;
