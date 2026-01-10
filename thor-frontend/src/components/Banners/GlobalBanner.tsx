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
  is_staff?: boolean;
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
  const [schwabHealth, setSchwabHealth] = useState<SchwabHealth | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
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

  // Live Schwab health updates via WebSocket
  useWsMessage<SchwabHealth>('schwab_health', (msg) => {
    if (msg?.data) {
      setSchwabHealth(msg.data);
      setLastUpdate(new Date());
    }
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

        const restored = accountId;
        if (restored && accountList.some((acct) => String(acct.broker_account_id) === String(restored))) {
          setAccountId(restored);
        } else {
          setAccountId(accountList[0]?.broker_account_id ?? null);
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
  // Intentionally run once on mount to hydrate accounts and set initial selection.
  // Do not include accountId; selection is owned by context and further changes come from user events.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setAccountId]);

  // selectedAccount is no longer used for balances; accountId is preserved for selection only

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
        schwabHealth={schwabHealth}
      />

      <BalanceRow
        balance={balance}
        loading={balanceLoading}
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

