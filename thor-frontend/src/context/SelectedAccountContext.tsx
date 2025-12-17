import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { BANNER_SELECTED_ACCOUNT_ID_KEY } from "../constants/bannerKeys";

type SelectedAccountValue = {
  accountId: string | null;
  accountKey: string;
};

const SelectedAccountContext = createContext<SelectedAccountValue | undefined>(undefined);

export const SelectedAccountProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const qc = useQueryClient();
  const [accountId, setAccountId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(BANNER_SELECTED_ACCOUNT_ID_KEY);
      setAccountId(raw || null);
    } catch {
      setAccountId(null);
    }
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ accountId?: number | string }>).detail;
      const next = detail?.accountId != null ? String(detail.accountId) : null;

      setAccountId(next);

      // On account change, clear account-scoped queries so old data cannot stick.
      qc.cancelQueries();
      qc.removeQueries({
        predicate: (q) => {
          const key0 = Array.isArray(q.queryKey) ? q.queryKey[0] : undefined;
          return key0 !== "globalMarketsStatus"; // keep global if desired
        },
      });
    };

    window.addEventListener("thor:selectedAccountChanged", handler);
    return () => window.removeEventListener("thor:selectedAccountChanged", handler);
  }, [qc]);

  const accountKey = accountId ? `acct:${accountId}` : "acct:none";
  const value = useMemo(() => ({ accountId, accountKey }), [accountId, accountKey]);

  return <SelectedAccountContext.Provider value={value}>{children}</SelectedAccountContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export function useSelectedAccount() {
  const ctx = useContext(SelectedAccountContext);
  if (!ctx) throw new Error("useSelectedAccount must be used within SelectedAccountProvider");
  return ctx;
}
