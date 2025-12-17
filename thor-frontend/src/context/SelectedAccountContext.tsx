import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { BANNER_SELECTED_ACCOUNT_ID_KEY } from "../constants/bannerKeys";

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

export const SelectedAccountProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const qc = useQueryClient();
  const [accountId, _setAccountId] = useState<string | null>(null);

  // track previous key so we can cancel/remove *only old account* queries
  const prevAccountKeyRef = useRef<string>("acct:none");

  // hydrate initial account from sessionStorage (keeps current behavior)
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
      _setAccountId(raw || null);
    } catch {
      _setAccountId(null);
    }
  }, []);

  const setAccountId = useCallback((next: string | number | null) => {
    const id = toId(next);
    _setAccountId(id);

    // persist selection (keeps banner behavior stable)
    try {
      if (id) sessionStorage.setItem(BANNER_SELECTED_ACCOUNT_ID_KEY, id);
      else sessionStorage.removeItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
    } catch {
      /* ignore storage errors */
    }

  }, []);

  const accountKey = accountId ? `acct:${accountId}` : "acct:none";

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
