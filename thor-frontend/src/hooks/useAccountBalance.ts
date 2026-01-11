import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";
import { qk } from "../realtime/queryKeys";
import { useWsMessage } from "../realtime";

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

type BalanceWsPayload = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function toAccountBalance(payload: BalanceWsPayload): AccountBalance | null {
  const accountId = String(
    payload.account_id ?? payload.account_hash ?? payload.accountId ?? "",
  ).trim();
  if (!accountId) return null;

  const updatedAtRaw = payload.updated_at ?? payload.timestamp ?? payload.asof;
  const updatedAt = typeof updatedAtRaw === "string" && updatedAtRaw ? updatedAtRaw : new Date().toISOString();

  return {
    account_id: accountId,
    net_liquidation: asNumber(
      payload.net_liquidation ?? payload.net_liq ?? payload.netLiquidation ?? payload.liquidationValue,
    ),
    equity: asNumber(payload.equity ?? payload.equityValue),
    cash: asNumber(payload.cash ?? payload.cash_balance ?? payload.cashBalance),
    buying_power: asNumber(
      payload.buying_power ?? payload.stock_buying_power ?? payload.buyingPower ?? payload.marginBuyingPower,
    ),
    day_trade_bp: asNumber(payload.day_trade_bp ?? payload.day_trading_buying_power ?? payload.dayTradingBuyingPower),
    updated_at: updatedAt,
    source: typeof payload.source === "string" ? payload.source : "ws",
  };
}

async function fetchAccountBalance(accountId?: string | null) {
  const res = await api.get<AccountBalance>("/accounts/balance/", {
    params: accountId ? { account_id: accountId } : undefined,
  });
  return res.data;
}

export function useAccountBalance(accountId?: string | null) {
  const accountKey = accountId ? `acct:${accountId}` : "acct:none";
  const qc = useQueryClient();

  // Realtime balance snapshots (published via backend poller)
  useWsMessage<BalanceWsPayload>(
    "balances",
    (msg) => {
      const raw = msg?.data;
      if (!isRecord(raw)) return;

      const normalized = toAccountBalance(raw);
      if (!normalized) return;

      if (accountId && normalized.account_id !== String(accountId)) return;

      qc.setQueryData(qk.balances(accountKey), normalized);
    },
    Boolean(accountId)
  );

  const query = useQuery({
    queryKey: qk.balances(accountKey),
    queryFn: () => fetchAccountBalance(accountId),
    refetchInterval: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  return query;
}
