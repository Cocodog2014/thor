// thor-frontend/src/components/Banners/GlobalBanner.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';
import api from '../../services/api';
import type { AccountSummary, ParentTab, ChildTab, SchwabHealth } from './bannerTypes';
import TopRow from './TopRow';
import BalanceRow from './BalanceRow';
import TabsRow from './TabsRow';
import SchwabHealthCard from './SchwabHealthCard';
import { useAuth } from '../../context/AuthContext';
import { useSelectedAccount } from '../../context/SelectedAccountContext';
import { useAccountBalance } from '../../hooks/useAccountBalance';
import { useWsConnection, useWsMessage, wsEnabled } from '../../realtime';

type UserProfile = {
  id?: number;
  is_staff?: boolean;
};

type SchwabHealthBroadcastPayload = {
  timestamp?: number;
  connections?: Array<{
    user_id: number;
    broker: string;
    account_id?: string | null;
    trading_enabled?: boolean;
    expires_at?: number;
    seconds_until_expiry?: number;
    token_expired?: boolean;
    refreshed?: boolean;
    error?: string | null;
  }>;
};

// Permanent banner under the AppBar, shows connection/account info + balances + tabs.
const GlobalBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = useAuth();
  const { accountId, setAccountId } = useSelectedAccount();
  const { data: balance, isFetching: balanceLoading } = useAccountBalance(accountId);

  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Accounts + selected account for the dropdown
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [schwabHealth, setSchwabHealth] = useState<SchwabHealth | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [userId, setUserId] = useState<number | null>(null);
  const [nowUnix, setNowUnix] = useState(() => Math.floor(Date.now() / 1000));
  const [schwabServerNowBase, setSchwabServerNowBase] = useState<number | null>(null);
  const [schwabServerNowBaseClientNow, setSchwabServerNowBaseClientNow] = useState<number | null>(null);
  const selectedAccountId = accountId || null;

  // WebSocket connection status (single backend WS: /ws/ handled by api.websocket)
  const wsConnected = useWsConnection(true);
  const wsIsEnabled = wsEnabled();

  // Update the "last feed" timestamp using the backend heartbeat (low frequency)
  useWsMessage('heartbeat', () => {
    setLastUpdate(new Date());
  });

  useEffect(() => {
    let isMounted = true;

    const fetchHealth = async () => {
      try {
        const { data } = await api.get<SchwabHealth>('/schwab/health/');
        if (!isMounted) return;
        setSchwabHealth(data);

        // HTTP endpoint does not include server timestamp; use client clock until WS health arrives.
        setSchwabServerNowBase(null);
        setSchwabServerNowBaseClientNow(null);
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

    return () => {
      isMounted = false;
    };
  }, []);

  // Live Schwab health updates via WebSocket.
  // Backend broadcasts a global snapshot {timestamp, connections:[...]}.
  // Map it down to the current user/selected account.
  useWsMessage<SchwabHealthBroadcastPayload>('schwab_health', (msg) => {
    const payload = msg?.data;
    const rows = payload?.connections;
    if (!Array.isArray(rows) || rows.length === 0) return;

    if (typeof payload?.timestamp === 'number') {
      setSchwabServerNowBase(payload.timestamp);
      setSchwabServerNowBaseClientNow(Math.floor(Date.now() / 1000));
    }

    const bySelectedAccount = selectedAccountId
      ? rows.find((r) => r.account_id && String(r.account_id) === String(selectedAccountId))
      : undefined;

    const byUser = userId !== null
      ? rows.find((r) => r.user_id === userId)
      : undefined;

    const row = bySelectedAccount || byUser;
    if (!row) return;

    const tokenExpired = Boolean(row.token_expired);
    const tradingEnabled = Boolean(row.trading_enabled);

    setSchwabHealth({
      connected: !tokenExpired,
      broker: row.broker || 'SCHWAB',
      token_expired: tokenExpired,
      expires_at: row.expires_at,
      seconds_until_expiry: row.seconds_until_expiry,
      trading_enabled: tradingEnabled,
      approval_state: tradingEnabled ? 'trading_enabled' : 'read_only',
      last_error: row.error ?? null,
    });
    setLastUpdate(new Date());
  });

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
        setUserId(typeof data?.id === 'number' ? data.id : null);
        setIsAdmin(Boolean(data?.is_staff));
      } catch (error) {
        if (!active) return;
        console.error('GlobalBanner: failed to load profile for admin check', error);
        setIsAdmin(false);
        setUserId(null);
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
        const { data } = await api.get<{ accounts?: AccountSummary[] } | AccountSummary[]>('/actandpos/accounts');
        const accountList = Array.isArray(data)
          ? data
          : Array.isArray(data?.accounts)
            ? data.accounts
            : [];
        if (!isMounted) return;

        setAccounts(accountList);
      } catch (error) {
        if (!isMounted) return;
        console.error('Failed to load accounts list', error);
        setAccounts([]);
      }

      if (!isMounted) return;
      setAccountsLoaded(true);
    };

    loadAccounts();

    return () => {
      isMounted = false;
    };
  // Intentionally run once on mount to hydrate accounts and set initial selection.
  }, []);

  // Reconcile selected account once accounts are loaded.
  // - If there's a valid restored selection, keep it.
  // - Otherwise default to the first account returned by the backend.

  const effectiveSchwabHealth = useMemo(() => {
    if (!schwabHealth) return null;
    const expiresAt = schwabHealth.expires_at;
    if (!expiresAt) return schwabHealth;

    const effectiveNow = (schwabServerNowBase !== null && schwabServerNowBaseClientNow !== null)
      ? (schwabServerNowBase + (nowUnix - schwabServerNowBaseClientNow))
      : nowUnix;

    const secondsLeft = Math.max(0, Math.floor(expiresAt - effectiveNow));
    const tokenExpired = secondsLeft <= 0;

    return {
      ...schwabHealth,
      seconds_until_expiry: secondsLeft,
      token_expired: tokenExpired,
      connected: schwabHealth.connected && !tokenExpired,
    } as SchwabHealth;
  }, [schwabHealth, nowUnix, schwabServerNowBase, schwabServerNowBaseClientNow]);

  useEffect(() => {
    if (!accountsLoaded) return;

    if (accounts.length === 0) {
      // Don't blow away a restored selection during transient errors.
      // If backend says there are no accounts, clear selection.
      if (accountId) setAccountId(null);
      return;
    }

    const selected = accountId
      ? accounts.find((acct) => String(acct.broker_account_id) === String(accountId))
      : undefined;

    const paper = accounts.find((acct) => String(acct.broker).toUpperCase() === 'PAPER');
    const schwab = accounts.find((acct) => String(acct.broker).toUpperCase() === 'SCHWAB');
    const schwabConnected = Boolean(effectiveSchwabHealth?.connected);

    // Default selection should match what's actually usable:
    // - If Schwab is connected, prefer it.
    // - Otherwise prefer Paper (if present), else fallback to whatever we have.
    const preferred = (schwabConnected ? schwab : (paper ?? schwab)) ?? accounts[0];

    // If a restored selection is valid, keep it.
    // Preserve explicit user selection even if Schwab isn't connected;
    // the banner status will reflect connection state.
    if (selected) {
      return;
    }

    setAccountId(preferred?.broker_account_id ?? null);
  }, [accountsLoaded, accounts, accountId, setAccountId, effectiveSchwabHealth?.connected]);

  // selectedAccount is no longer used for balances; accountId is preserved for selection only

  // Client-side Schwab countdown: update once per second so the UI stays "alive" even if
  // backend health broadcasts are infrequent.
  useEffect(() => {
    const expiresAt = schwabHealth?.expires_at;
    if (!expiresAt) return;

    const interval = window.setInterval(() => {
      setNowUnix(Math.floor(Date.now() / 1000));
    }, 1000);

    return () => {
      window.clearInterval(interval);
    };
  }, [schwabHealth?.expires_at]);

  const isConnected = wsIsEnabled && wsConnected;
  const connectionLabel = wsIsEnabled ? (isConnected ? 'Connected' : 'Disconnected') : 'Disabled';
  const connectionDetails = wsIsEnabled
    ? (isConnected
        ? `WebSocket connected${lastUpdate ? ` · last feed ${lastUpdate.toLocaleTimeString('en-US')}` : ''}`
        : 'WebSocket disconnected')
    : 'Realtime disabled';

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
        schwabHealth={effectiveSchwabHealth}
      />

      <BalanceRow
        balance={balance}
        loading={balanceLoading}
      />

      {isAdmin && <SchwabHealthCard health={effectiveSchwabHealth} />}

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

