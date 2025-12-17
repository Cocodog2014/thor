import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import api from "../../../services/api";

type SchwabAccount = {
  broker_account_id?: string;
  display_name?: string;
};

type SchwabSummary = {
  trading_enabled?: boolean;
};

export default function BrokersPage() {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<SchwabAccount[]>([]);
  const [summary, setSummary] = useState<SchwabSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isConnected = accounts.length > 0;
  const tradingEnabled = Boolean(summary?.trading_enabled);
  const justConnected = new URLSearchParams(location.search).get("connected") === "1";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [acctRes, summaryRes] = await Promise.allSettled([
        api.get("schwab/accounts/"),
        api.get("schwab/account/summary/"),
      ]);

      if (acctRes.status === "fulfilled") {
        setAccounts(Array.isArray(acctRes.value.data) ? acctRes.value.data : []);
      } else {
        setAccounts([]);
      }

      if (summaryRes.status === "fulfilled") {
        setSummary(summaryRes.value.data ?? null);
      } else {
        setSummary(null);
      }
    } catch {
      setError("Failed to load broker status.");
    } finally {
      setLoading(false);
    }
  }, []);

  const connectSchwab = async () => {
    setError(null);
    try {
      const res = await api.get("schwab/oauth/start/");
      const authUrl = res.data?.auth_url;
      if (!authUrl) {
        setError("No auth_url returned from server.");
        return;
      }
      window.location.href = authUrl;
    } catch {
      setError("Failed to start Schwab connection.");
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!justConnected) {
      return;
    }

    setNotice("Schwab connection updated. Refreshing data…");
    load();
    const timeout = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timeout);
  }, [justConnected, load]);

  const statusText = loading
    ? "Loading…"
    : !isConnected
    ? "Not connected"
    : tradingEnabled
    ? "Live trading enabled"
    : "Connected (read-only)";

  return (
    <div className="brokers-page">
      <h2 className="brokers-title">Broker Connections</h2>
      <p className="brokers-subtitle">
        Balances/positions can sync in read-only mode. Live orders require admin approval.
      </p>

      {error && (
        <div className="brokers-error">
          <strong>{error}</strong>
        </div>
      )}

      {notice && (
        <div className="brokers-notice">
          <strong>{notice}</strong>
        </div>
      )}

      <div className="brokers-card">
        <div className="brokers-card__header">
          <h3>Charles Schwab</h3>
          <span>{statusText}</span>
        </div>

        <hr />

        {!isConnected ? (
          <p className="brokers-copy">
            Connect your Schwab account to sync balances and positions.
          </p>
        ) : (
          <div className="brokers-accounts">
            <div className="brokers-accounts__title">Connected accounts:</div>
            <ul>
              {accounts.map((a, idx) => (
                <li key={idx}>
                  {a.display_name ?? "Schwab Account"} ({a.broker_account_id ?? "—"})
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="brokers-actions">
          <button onClick={connectSchwab}>
            {isConnected ? "Reconnect Schwab" : "Connect Schwab"}
          </button>
          <button onClick={load}>Refresh</button>
        </div>
      </div>

      <div className="brokers-card">
        <h3>International Broker</h3>
        <p className="brokers-copy">Coming next: API key connection form.</p>
      </div>
    </div>
  );
}
