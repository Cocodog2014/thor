// src/pages/ActivityPositions/ActivityPositions.tsx
import React, { useEffect, useState } from "react";
import "./ActivityPositions.css";
import api from "../../services/api";
import toast from "react-hot-toast";

// ---------- Types matching ActAndPos API ----------

interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string | null;
  currency: string;
  net_liq: string;
  cash: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}

interface Order {
  id: number;
  symbol: string;
  asset_type: string;
  side: "BUY" | "SELL";
  quantity: string;
  order_type: string;
  limit_price: string | null;
  stop_price: string | null;
  status: string;
  time_placed: string;
  time_last_update: string;
  time_filled: string | null;
  time_canceled: string | null;
}

interface Position {
  id: number;
  symbol: string;
  description: string;
  asset_type: string;
  quantity: string;
  avg_price: string;
  mark_price: string;
  market_value: string;
  unrealized_pl: string;
  pl_percent: string;
  realized_pl_open: string;
  realized_pl_day: string;
  currency: string;
}

interface ActivityTodayResponse {
  account: AccountSummary;
  working_orders: Order[];
  filled_orders: Order[];
  canceled_orders: Order[];
  positions: Position[];
  account_status: {
    ok_to_trade: boolean;
    net_liq: string | number;
    day_trading_buying_power: string | number;
  };
}

interface PaperOrderResponse {
  account: AccountSummary;
  order: Order;
  position: Position | null;
}

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

const PaperOrderTicket: React.FC<{ account: AccountSummary; onOrderPlaced: () => void }> = ({
  account,
  onOrderPlaced,
}) => {
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("1");
  const [orderType, setOrderType] = useState<"MKT" | "LMT">("MKT");
  const [limitPrice, setLimitPrice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const sym = symbol.trim().toUpperCase();
    if (!sym) {
      toast.error("Symbol is required.");
      return;
    }

    const qty = Number(quantity);
    if (!qty || qty <= 0) {
      toast.error("Quantity must be greater than zero.");
      return;
    }

    if (orderType === "LMT" && !limitPrice.trim()) {
      toast.error("Limit price is required for limit orders.");
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        symbol: sym,
        asset_type: "EQ",
        side,
        quantity: qty,
        order_type: orderType,
        limit_price: orderType === "LMT" ? Number(limitPrice.trim()) : null,
        stop_price: null,
      };

      const response = await api.post<PaperOrderResponse>("/actandpos/paper/order", payload);
      toast.success(
        `Paper ${response.data.order.side} ${response.data.order.quantity} ${response.data.order.symbol} submitted.`,
      );

      setSymbol("");
      setQuantity("1");
      setLimitPrice("");
      onOrderPlaced();
    } catch (err: any) {
      console.error("[PaperOrderTicket] Failed to place order", err);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Failed to place paper order.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="ap-paper-ticket">
      <div className="ap-paper-ticket-title">
        Paper Trading – Quick Ticket ({account.display_name || account.broker_account_id})
      </div>
      <form className="ap-paper-ticket-form" onSubmit={handleSubmit}>
        <label>
          Symbol
          <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="ES, AAPL, etc." />
        </label>
        <label>
          Side
          <select value={side} onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>
        <label>
          Qty
          <input type="number" min={0} step="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </label>
        <label>
          Type
          <select value={orderType} onChange={(e) => setOrderType(e.target.value as "MKT" | "LMT")}>
            <option value="MKT">Market</option>
            <option value="LMT">Limit</option>
          </select>
        </label>
        <label>
          Limit
          <input
            type="number"
            step="0.01"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            disabled={orderType !== "LMT"}
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Sending…" : "Send Paper Order"}
        </button>
      </form>
    </div>
  );
};

// ---------- Main component ----------

const ActivityPositions: React.FC = () => {
  const [data, setData] = useState<ActivityTodayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const response = await api.get<ActivityTodayResponse>("/actandpos/activity/today");
        if (!cancelled) {
          setData(response.data);
          setError(null);
        }
      } catch (err) {
        console.error("[ActivityPositions] Failed to load activity.", err);
        if (!cancelled) setError("Failed to load activity and positions.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const interval = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refreshCounter]);

  if (loading && !data) {
    return (
      <div className="ap-screen">
        <div className="ap-body">Loading activity and positions…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ap-screen">
        <div className="ap-body ap-error">{error}</div>
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
        </div>

        {/* NEW: Paper order ticket */}
        <PaperOrderTicket
          account={account}
          onOrderPlaced={() => setRefreshCounter((prev) => prev + 1)}
        />

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
