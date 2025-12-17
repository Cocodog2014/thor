import { useQuery } from "@tanstack/react-query";
import api from "../services/api";

export type AccountBalance = {
  account_id: string;
  net_liquidation: number;
  equity: number;
  cash: number;
  buying_power: number;
  day_trade_bp: number;
  updated_at: string;
  source?: string;
};

async function fetchAccountBalance(accountId?: string | null) {
  const res = await api.get<AccountBalance>("/accounts/balance/", {
    params: accountId ? { account_id: accountId } : undefined,
  });
  return res.data;
}

export function useAccountBalance(accountId?: string | null, refreshMs = 1000) {
  const accountKey = accountId ? `acct:${accountId}` : "acct:none";

  return useQuery({
    queryKey: ["accountBalance", accountKey],
    queryFn: () => fetchAccountBalance(accountId),
    refetchInterval: refreshMs,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
