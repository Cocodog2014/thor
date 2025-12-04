// MarketSessionCard.tsx
import React from "react";
import { getSessionDateKey, isToday } from "./marketSessionUtils.ts";
import MarketTotalCard from "./MarketTotalCard";
import MarketFutureCard from "./MarketFutureCard";

type MarketSessionCardProps = {
  market: any;                 // one element from CONTROL_MARKETS
  rows: any[];                 // rows for this country
  status?: any;                // liveStatus[m.country]
  intradaySnap?: any;          // intradayLatest[m.key]
  selectedSymbol?: string;     // selected[m.key]
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketSessionCard: React.FC<MarketSessionCardProps> = ({
  market: m,
  rows,
  status,
  intradaySnap,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
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

  const latestIntradaySnap = intradaySnap;

  if (!snap) {
    return (
      <div className="mo-rt-card">
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
        selectedSymbol={effectiveSelectedSymbol}
        onSelectedSymbolChange={onSelectedSymbolChange}
      />
    );
  }

  return (
    <MarketFutureCard
      market={m}
      snap={snap}
      intradaySnap={latestIntradaySnap}
      selectedSymbol={effectiveSelectedSymbol}
      onSelectedSymbolChange={onSelectedSymbolChange}
    />
  );
};

export default MarketSessionCard;
