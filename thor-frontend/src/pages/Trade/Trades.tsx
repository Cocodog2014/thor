import React, { useEffect, useState } from "react";
import "./Trades.css";
import toast from "react-hot-toast";
import api from "../../services/api";
import type {
  AccountSummary,
  ActivityTodayResponse,
  PaperOrderResponse,
} from "../../types/actandpos";

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

      const response = await api.post<PaperOrderResponse>("/trades/paper/order", payload);
      toast.success(
        `Paper ${response.data.order.side} ${response.data.order.quantity} ${response.data.order.symbol} submitted.`,
      );

      setSymbol("");
      setQuantity("1");
      setLimitPrice("");
      onOrderPlaced();
    } catch (err: any) {
      console.error("[TradeTicket] Failed to place order", err);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Failed to place paper order.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="trade-ticket">
      <div className="trade-ticket-title">
        Paper Trading – Quick Ticket ({account.display_name || account.broker_account_id})
      </div>
      <form className="trade-ticket-form" onSubmit={handleSubmit}>
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

const Trades: React.FC = () => {
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadAccount() {
      try {
        setLoading(true);
        const response = await api.get<ActivityTodayResponse>("/actandpos/activity/today");
        if (!cancelled) {
          setAccount(response.data.account);
          setError(null);
        }
      } catch (err) {
        console.error("[Trades] Failed to load account", err);
        if (!cancelled) setError("Failed to load account information.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAccount();

    return () => {
      cancelled = true;
    };
  }, [refreshCounter]);

  if (loading && !account) {
    return (
      <div className="trade-screen">
        <div className="trade-body">Loading trade workspace…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="trade-screen">
        <div className="trade-body trade-error">{error}</div>
      </div>
    );
  }

  if (!account) {
    return null;
  }

  return (
    <div className="trade-screen">
      <header className="trade-header">
        <div>
          <h1>Trade Workspace</h1>
          <p>We are building out the full experience. For now, use the paper ticket to send test orders.</p>
        </div>
        <button
          type="button"
          className="trade-refresh"
          onClick={() => setRefreshCounter((prev) => prev + 1)}
        >
          Refresh Account
        </button>
      </header>

      <div className="trade-body">
        <PaperOrderTicket account={account} onOrderPlaced={() => setRefreshCounter((prev) => prev + 1)} />
      </div>
    </div>
  );
};

export default Trades;
