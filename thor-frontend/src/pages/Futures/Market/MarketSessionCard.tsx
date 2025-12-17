// MarketSessionCard.tsx
import React from "react";
import { getSessionDateKey, isToday } from "./marketSessionUtils";
import { CONTROL_MARKETS, type IntradayHealth, type MarketLiveStatus, type MarketOpenSession } from "./marketSessionTypes";
import MarketTotalCard from "./MarketTotalCard";
import MarketFutureCard from "./MarketFutureCard";

type MarketSessionCardProps = {
  market: (typeof CONTROL_MARKETS)[number];             // one element from CONTROL_MARKETS
  rows: MarketOpenSession[];             // rows for this country
  status?: MarketLiveStatus;            // liveStatus[m.country]
  health?: IntradayHealth; // intraday freshness
  selectedSymbol?: string; // selected[m.key]
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketSessionCard: React.FC<MarketSessionCardProps> = ({
  market: m,
  rows,
  status,
  health,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  const healthStatus = health?.status || "unknown";
  const healthClass =
    healthStatus === "green" ? "chip success" : healthStatus === "red" ? "chip error" : "chip default";
  const lastBarLocal = health?.last_bar_utc ? new Date(health.last_bar_utc).toLocaleTimeString() : "—";
  const lagLabel =
    typeof health?.lag_minutes === "number"
      ? `${health.lag_minutes.toFixed(1)}m lag`
      : "No bars yet";

  const renderHealth = () => (
    <div className="mo-rt-health-row">
      <span className={healthClass}>
        Intraday {healthStatus === "green" ? "Live" : healthStatus === "red" ? "Stalled" : "Unknown"}
      </span>
      <span className="chip default">Last bar {lastBarLocal}</span>
      <span className="chip default">{lagLabel}</span>
    </div>
  );

  // ----- prior-day / open hiding logic -----
  const latestRow =
    rows.length > 0
      ? rows.reduce((latest, r) =>
          new Date(r.captured_at) > new Date(latest.captured_at) ? r : latest
        )
      : null;

  const seconds = status?.seconds_to_next_event ?? undefined;
  const nextEvent = status?.next_event;

  const sessionDateKey = latestRow ? getSessionDateKey(latestRow) : undefined;
  const marketDateKey = status?.local_date_key;

  let isPriorDay = false;
  if (sessionDateKey && marketDateKey) {
    isPriorDay = sessionDateKey !== marketDateKey;
  } else if (latestRow?.captured_at) {
    isPriorDay = !isToday(latestRow.captured_at);
  }

  const hidePriorNow =
    isPriorDay &&
    nextEvent === "open" &&
    typeof seconds === "number" &&
    seconds <= 300;

  if (hidePriorNow) {
    return (
      <div className="mo-rt-card">
        {renderHealth()}
        <div className="mo-rt-left">
          <div className="mo-rt-header">
            <div className="mo-rt-header-chips">
              <span className="chip sym">{m.label}</span>
              <span className="chip default">Awaiting market open…</span>
            </div>
          </div>
          <div className="mo-rt-placeholder">
            Prior capture hidden 5 minutes before today&apos;s open.
          </div>
        </div>
      </div>
    );
  }

  // ----- select / snapshot -----
  const defaultFuture = "TOTAL";
  const effectiveSelectedSymbol = selectedSymbol || defaultFuture;

  const snap =
    rows.find(
      (r) =>
        r.future &&
        r.future.toUpperCase() === effectiveSelectedSymbol.toUpperCase()
    ) || rows[0];

  if (!snap) {
    return (
      <div className="mo-rt-card">
        {renderHealth()}
        <div className="mo-rt-left">
          <div className="mo-rt-header">
            <div className="mo-rt-header-chips">
              <span className="chip sym">{m.label}</span>
              <span className="chip default">No capture yet</span>
            </div>
          </div>
          <div className="mo-rt-placeholder">
            No market capture has been recorded for this session yet.
          </div>
        </div>
      </div>
    );
  }

  const isTotalFuture = (snap.future || "").toUpperCase() === "TOTAL";

  // ----- delegate to specific card -----
  if (isTotalFuture) {
    return (
      <MarketTotalCard
        market={m}
        snap={snap}
        health={health}
        selectedSymbol={effectiveSelectedSymbol}
        onSelectedSymbolChange={onSelectedSymbolChange}
      />
    );
  }

  return (
    <MarketFutureCard
      market={m}
      snap={snap}
      health={health}
      selectedSymbol={effectiveSelectedSymbol}
      onSelectedSymbolChange={onSelectedSymbolChange}
    />
  );
};

export default MarketSessionCard;
