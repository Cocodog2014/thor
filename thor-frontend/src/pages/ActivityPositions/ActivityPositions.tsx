// src/pages/ActivityPositions/ActivityPositions.tsx
import React from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../../services/api";
import { useSelectedAccount } from "../../context/SelectedAccountContext";
import type {
  ActivityTodayResponse,
  Order,
  Position,
} from "../../types/actandpos";

// ---------- Small presentational helpers ----------

const OrdersSection: React.FC<{ title: string; orders: Order[] }> = ({
  title,
  orders,
}) => (
  <section className="ap-section">
    <div className="ap-section-header">
      <span>{title}</span>
      <span className="ap-section-count">Orders: {orders.length}</span>
    </div>
    <div className="ap-table-wrapper">
      {orders.length === 0 ? (
        <div className="ap-table-empty">No records.</div>
      ) : (
        <table className="ap-table ap-table-orders">
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Symbol</th>
              <th>Type</th>
              <th>Limit</th>
              <th>Stop</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>{new Date(o.time_placed).toLocaleTimeString()}</td>
                <td>{o.side}</td>
                <td>{o.quantity}</td>
                <td>{o.symbol}</td>
                <td>{o.order_type}</td>
                <td>{o.limit_price ?? "-"}</td>
                <td>{o.stop_price ?? "-"}</td>
                <td>{o.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </section>
);

const PositionsStatement: React.FC<{ positions: Position[] }> = ({
  positions,
}) => (
  <section className="ap-section ap-section-positions">
    <div className="ap-section-header">
      <span>Position Statement</span>
      {/* place for “Beta Weighting / NOT WEIGHTED” later */}
    </div>
    <div className="ap-table-wrapper">
      {positions.length === 0 ? (
        <div className="ap-table-empty">No open positions.</div>
      ) : (
        <table className="ap-table ap-table-positions">
          <thead>
            <tr>
              <th>Instrument</th>
              <th>Qty</th>
              <th>Trade Price</th>
              <th>Mark</th>
              <th>Net Liq</th>
              <th>% Change</th>
              <th>P/L Open</th>
              <th>P/L Day</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.id}>
                <td>{p.symbol}</td>
                <td>{p.quantity}</td>
                <td>{p.avg_price}</td>
                <td>{p.mark_price}</td>
                <td>{p.market_value}</td>
                <td>{p.pl_percent}</td>
                <td>{p.realized_pl_open || p.unrealized_pl}</td>
                <td>{p.realized_pl_day}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </section>
);

// ---------- Main component ----------

const ActivityPositions: React.FC = () => {
  const { accountId, accountKey } = useSelectedAccount();

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["activityToday", accountKey],
    queryFn: async () => {
      const res = await api.get<ActivityTodayResponse>("/actandpos/activity/today", {
        params: accountId ? { account_id: accountId } : {},
      });
      return res.data;
    },
    enabled: !!accountId,
    refetchInterval: 15000,
    staleTime: 0,
    refetchOnMount: "always",
    keepPreviousData: false,
  });

  if (isLoading && !data) {
    return (
      <div className="ap-screen">
        <div className="ap-body">Loading activity and positions…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ap-screen">
        <div className="ap-body ap-error">Failed to load activity and positions.</div>
      </div>
    );
  }

  if (!data) return null;

  const { account, account_status } = data;

  return (
    <div className="ap-screen">
      <div className="ap-body">
        {/* Today’s Trade Activity header */}
        <div className="ap-title-row">
          <h2 className="ap-title">Today&apos;s Trade Activity</h2>
          <div className="ap-title-right">
            <div className="ap-account-summary">
            <span className="ap-label">Account:</span>{" "}
            <span className="ap-value">
              {account.display_name || account.broker_account_id}
            </span>
            <span className="ap-label">Net Liq:</span>{" "}
            <span className="ap-value">{account.net_liq}</span>
            <span className="ap-label">BP:</span>{" "}
            <span className="ap-value">
              {account.day_trading_buying_power}
            </span>
            </div>
            <button
              type="button"
              className="ap-refresh-button"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Orders sections */}
        <OrdersSection
          title="Working Orders"
          orders={data.working_orders}
        />
        <OrdersSection title="Filled Orders" orders={data.filled_orders} />
        <OrdersSection
          title="Canceled Orders"
          orders={data.canceled_orders}
        />

        {/* (Rolling Strategies / Covered Call Position headers could go here later) */}

        {/* Position Statement */}
        <PositionsStatement positions={data.positions} />

        {/* Account Status footer */}
        <div className="ap-status-row">
          <span className="ap-label">ACCOUNT STATUS:</span>{" "}
          <span
            className={
              account_status.ok_to_trade
                ? "ap-status-ok"
                : "ap-status-warning"
            }
          >
            {account_status.ok_to_trade ? "OK TO TRADE" : "REVIEW REQUIRED"}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ActivityPositions;
