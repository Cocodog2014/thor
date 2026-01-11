import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { BANNER_SELECTED_ACCOUNT_ID_KEY } from "../constants/bannerKeys";
import { setActiveAccountId } from "../realtime/router";

type SelectedAccountValue = {
  accountId: string | null;
  accountKey: string; // acct:<id> or acct:none
  setAccountId: (next: string | number | null) => void;
};

const SelectedAccountContext = createContext<SelectedAccountValue | undefined>(undefined);

function toId(next: string | number | null | undefined): string | null {
  if (next === null || next === undefined) return null;
  const s = String(next).trim();
  return s ? s : null;
}

function readStoredAccountId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    // Prefer localStorage so refresh/new tab retains selection.
    const fromLocal = window.localStorage.getItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
    if (fromLocal) return fromLocal;
  } catch {
    /* ignore storage errors */
  }

  try {
    // Back-compat with earlier sessionStorage persistence.
    const fromSession = window.sessionStorage.getItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
    return fromSession || null;
  } catch {
    return null;
  }
}

export const SelectedAccountProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const qc = useQueryClient();
  const [accountId, _setAccountId] = useState<string | null>(() => readStoredAccountId());

  // track previous key so we can cancel/remove *only old account* queries
  const prevAccountKeyRef = useRef<string>("acct:none");

  const setAccountId = useCallback((next: string | number | null) => {
    const id = toId(next);
    _setAccountId(id);

    // persist selection
    try {
      if (id) window.localStorage.setItem(BANNER_SELECTED_ACCOUNT_ID_KEY, id);
      else window.localStorage.removeItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
    } catch {
      /* ignore storage errors */
    }

    // Also write sessionStorage so existing flows remain stable.
    try {
      if (id) window.sessionStorage.setItem(BANNER_SELECTED_ACCOUNT_ID_KEY, id);
      else window.sessionStorage.removeItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
    } catch {
      /* ignore storage errors */
    }

  }, []);

  const accountKey = accountId ? `acct:${accountId}` : "acct:none";

  // Ensure WS only mutates the currently-selected account view.
  useEffect(() => {
    setActiveAccountId(accountId);
    return () => setActiveAccountId(null);
  }, [accountId]);

  // On account change: cancel/remove only the previous account’s cache
  useEffect(() => {
    const prevKey = prevAccountKeyRef.current;
    const nextKey = accountKey;

    if (prevKey !== nextKey) {
      // cancel in-flight for previous account
      qc.cancelQueries({
        predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[1] === prevKey,
      });

      // remove cached queries for previous account to prevent “flash”
      qc.removeQueries({
        predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[1] === prevKey,
      });

      prevAccountKeyRef.current = nextKey;
    }
  }, [accountKey, qc]);

  // Legacy event dispatch/listen removed to prevent double-dispatch and keep context authoritative

  const value = useMemo(() => ({ accountId, accountKey, setAccountId }), [accountId, accountKey, setAccountId]);

  return <SelectedAccountContext.Provider value={value}>{children}</SelectedAccountContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export function useSelectedAccount() {
  const ctx = useContext(SelectedAccountContext);
  if (!ctx) throw new Error("useSelectedAccount must be used within SelectedAccountProvider");
  return ctx;
}
