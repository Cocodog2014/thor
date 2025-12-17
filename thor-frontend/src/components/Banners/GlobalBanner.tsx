// GlobalBanner.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';
import api from '../../services/api';
import type { AccountSummary, ParentTab, ChildTab, SchwabHealth } from './bannerTypes';
import TopRow from './TopRow';
import BalanceRow from './BalanceRow';
import TabsRow from './TabsRow';
import SchwabHealthCard from './SchwabHealthCard';
import { useGlobalTimer } from '../../context/GlobalTimerContext';
import { useAuth } from '../../context/AuthContext';
import { useSelectedAccount } from '../../context/SelectedAccountContext';

type UserProfile = {
  is_staff?: boolean;
};

// Permanent banner under the AppBar, shows connection/account info + balances + tabs.
const GlobalBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { now } = useGlobalTimer();
  const { token } = useAuth();
  const { accountId, setAccountId } = useSelectedAccount();

  const [connectionStatus, setConnectionStatus] =
    useState<'connected' | 'disconnected'>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  // Accounts + selected account for the dropdown
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [schwabHealth, setSchwabHealth] = useState<SchwabHealth | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const selectedAccountId = accountId ? Number(accountId) || null : null;

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

  useEffect(() => {
    let isMounted = true;

    const fetchHealth = async () => {
      try {
        const { data } = await api.get<SchwabHealth>('/schwab/health/');
        if (!isMounted) return;
        setSchwabHealth(data);
      } catch (error) {
        if (!isMounted) return;
        console.error('GlobalBanner: failed to fetch Schwab health', error);
        setSchwabHealth({
          connected: false,
          broker: 'SCHWAB',
          token_expired: true,
          last_error: 'Unable to reach Schwab health endpoint',
          approval_state: 'not_connected',
        });
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let active = true;

    if (!token) {
      setIsAdmin(false);
      return () => {
        active = false;
      };
    }

    const fetchProfile = async () => {
      try {
        const { data } = await api.get<UserProfile>('/users/profile/');
        if (!active) return;
        setIsAdmin(Boolean(data?.is_staff));
      } catch (error) {
        if (!active) return;
        console.error('GlobalBanner: failed to load profile for admin check', error);
        setIsAdmin(false);
      }
    };

    fetchProfile();

    return () => {
      active = false;
    };
  }, [token]);

  // Load all accounts for the account selector in the banner
  useEffect(() => {
    let isMounted = true;

    const loadAccounts = async () => {
      try {
        const { data } = await api.get<AccountSummary[]>('/actandpos/accounts');
        const accountList = Array.isArray(data) ? data : [];
        if (!isMounted) return;

        setAccounts(accountList);

        if (accountList.length === 0) {
          setAccountId(null);
          return;
        }

        const restored = selectedAccountId;
        if (restored && accountList.some((acct) => acct.id === restored)) {
          setAccountId(restored);
        } else {
          setAccountId(accountList[0]?.id ?? null);
        }
      } catch (error) {
        if (!isMounted) return;
        console.error('Failed to load accounts list', error);
        setAccounts([]);
        setAccountId(null);
      }
    };

    loadAccounts();

    return () => {
      isMounted = false;
    };
  }, [selectedAccountId, setAccountId]);

  const selectedAccount =
    (selectedAccountId !== null
      ? accounts.find((a) => a.id === selectedAccountId)
      : null) || null;

  const isConnected = connectionStatus === 'connected';
  const connectionLabel = isConnected ? 'Connected' : 'Disconnected';
  const realtimeClock = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const connectionDetails = isConnected
    ? `Realtime data · ${realtimeClock}${lastUpdate ? ` (last feed ${lastUpdate})` : ''}`
    : 'Waiting for live feed';

  // Parent (top) tabs
  const parentTabs: ParentTab[] = useMemo(
    () => [
      { label: 'Home', path: '/app/home', key: 'home' },
      { label: 'Trade', path: '/app/trade', key: 'trade' },
      { label: 'Futures', path: '/app/futures', key: 'futures' },
      { label: 'Global', path: '/app/global', key: 'global' },
    ],
    [],
  );

  // Child tabs for each parent (generic placeholders for now)
  const childTabsByParent: Record<string, ChildTab[]> = useMemo(
    () => ({
      home: [
        { label: 'Activity & Positions', path: '/app/activity' },
        { label: 'Account Statement', path: '/app/account-statement' },
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
    }),
    [],
  );

  // Helper to derive parent key from current location
  const deriveParentKey = useCallback(
    (pathname: string) =>
      parentTabs.find((tab) => pathname.startsWith(tab.path))?.key ?? parentTabs[0].key,
    [parentTabs],
  );

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
  }, [location.pathname, activeParentKey, deriveParentKey]);

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
        onAccountChange={(id) => setAccountId(id)}
        onNavigate={(path) => navigate(path)}
        schwabHealth={schwabHealth}
      />

      <BalanceRow
        selectedAccount={selectedAccount}
        formatCurrency={formatCurrency}
      />

      {isAdmin && <SchwabHealthCard health={schwabHealth} />}

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

