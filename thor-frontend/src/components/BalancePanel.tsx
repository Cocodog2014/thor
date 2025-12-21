import { useAccountBalance } from "../hooks/useAccountBalance";

export default function BalancePanel({
  accountId,
}: {
  accountId?: string | null;
}) {
  const { data, isLoading, isError } = useAccountBalance(accountId);

  if (isLoading) return <div className="panel">Loading balance…</div>;
  if (isError || !data) return <div className="panel error">No balance data</div>;

  return (
    <div className="panel balance-panel">
      <div className="row"><span>Net Liq</span><strong>${data.net_liquidation.toFixed(2)}</strong></div>
      <div className="row"><span>Equity</span><strong>${data.equity.toFixed(2)}</strong></div>
      <div className="row"><span>Cash</span><strong>${data.cash.toFixed(2)}</strong></div>
      <div className="row"><span>Buying Power</span><strong>${data.buying_power.toFixed(2)}</strong></div>
      <div className="row"><span>Day Trade BP</span><strong>${data.day_trade_bp.toFixed(2)}</strong></div>
      <div className="timestamp">
        Updated {new Date(data.updated_at).toLocaleTimeString()}
      </div>
    </div>
  );
}
