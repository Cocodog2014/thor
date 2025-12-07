// GlobalBanner.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';
import api from '../../services/api';
import type { AccountSummary, ParentTab, ChildTab } from './bannerTypes';
import TopRow from './TopRow';
import BalanceRow from './BalanceRow';
import TabsRow from './TabsRow';

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

  // Ping the same quotes endpoint used by the futures hooks
  useEffect(() => {
    let isMounted = true;

    const checkConnection = async () => {
      try {
        const response = await fetch('/api/quotes/latest?consumer=futures_trading', {
          cache: 'no-store',
        });

        if (!response.ok) {
          throw new Error(`Status ${response.status}`);
        }

        const data: { rows?: unknown[] } = await response.json();
        const rows = Array.isArray(data?.rows) ? data.rows : [];
        const hasLiveData = rows.length > 0;

        if (!isMounted) return;

        if (hasLiveData) {
          setConnectionStatus('connected');
          setLastUpdate(new Date().toLocaleTimeString());
        } else {
          setConnectionStatus('disconnected');
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('GlobalBanner: error checking connection', err);
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
        const { data } = await api.get<AccountSummary[]>('/actandpos/accounts');
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
  const parentTabs: ParentTab[] = [
    { label: 'Home', path: '/app/home', key: 'home' },
    { label: 'Trade', path: '/app/trade', key: 'trade' },
    { label: 'Futures', path: '/app/futures', key: 'futures' },
    { label: 'Global', path: '/app/global', key: 'global' },
  ];

  // Child tabs for each parent (generic placeholders for now)
  const childTabsByParent: Record<string, ChildTab[]> = {
    home: [
      { label: 'Activity & Positions', path: '/app/activity' },
      { label: 'Account Statement', path: '/app/account-statement' },
      { label: 'FX Report', path: '/app/home' },
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

  return (
    <div
      className="global-banner"
      role="navigation"
      aria-label="Primary navigation banner"
    >
      <TopRow
        isConnected={isConnected}
        connectionLabel={connectionLabel}
        connectionDetails={connectionDetails}
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        onAccountChange={(id) => setSelectedAccountId(id)}
        onNavigate={(path) => navigate(path)}
      />

      <BalanceRow
        selectedAccount={selectedAccount}
        formatCurrency={formatCurrency}
      />

      <TabsRow
        parentTabs={parentTabs}
        childTabsByParent={childTabsByParent}
        activeParentKey={activeParentKey}
        onParentClick={handleParentClick}
        onChildClick={handleChildClick}
        locationPathname={location.pathname}
      />
    </div>
  );
};

export default GlobalBanner;

