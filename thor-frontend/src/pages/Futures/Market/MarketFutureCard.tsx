// MarketFutureCard.tsx
import React from "react";
import { CONTROL_MARKETS, FUTURE_OPTIONS, type IntradayHealth, type MarketOpenSession } from "./marketSessionTypes.ts";
import {
  chipClass,
  formatNum,
  formatSignedValue,
  formatPercentValue,
  getDeltaClass,
  getTriangleClass,
  buildPercentCell,
  isZero,
  formatNumOrDash,
  getSessionDateKey,
} from "./marketSessionUtils.ts";

type MarketFutureCardProps = {
  market: (typeof CONTROL_MARKETS)[number];
  snap: MarketOpenSession;
  health?: IntradayHealth;
  selectedSymbol: string;
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketFutureCard: React.FC<MarketFutureCardProps> = ({
  market: m,
  snap,
  health,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  const signal = snap?.bhs;
  const outcomeStatus = snap?.wndw;

  const healthStatus = health?.status || "unknown";
  const healthClass =
    healthStatus === "green" ? "chip success" : healthStatus === "red" ? "chip error" : "chip default";
  const lastBarLocal = health?.last_bar_utc ? new Date(health.last_bar_utc).toLocaleTimeString() : "—";
  const lagLabel =
    typeof health?.lag_minutes === "number"
      ? `${health.lag_minutes.toFixed(1)}m lag`
      : "No bars yet";

  const captureTime = snap?.captured_at
    ? new Date(snap.captured_at).toLocaleTimeString()
    : "—";
  const selectId = `future-select-${m.key}`;

  const sessionDateLabel = getSessionDateKey(snap) ?? "—";

  const closeDeltaValue = formatSignedValue(snap?.market_close);
  const closeDeltaPercent = formatPercentValue(
    snap?.market_close_vs_open_pct
  );
  const closeDeltaClass = getDeltaClass(
    snap?.market_close ??
      snap?.market_close_vs_open_pct ??
      snap?.market_high_pct_close ??
      snap?.market_low_pct_close
  );

  const bidPriceDisplay = formatNumOrDash(snap?.bid_price);
  const bidSizeDisplay = formatNumOrDash(snap?.bid_size, 0);
  const askPriceDisplay = formatNumOrDash(snap?.ask_price);
  const askSizeDisplay = formatNumOrDash(snap?.ask_size, 0);

  const lastPriceDisplay =
    formatNum(snap?.last_price) ?? (isZero(snap?.last_price) ? 0 : "—");

  // Summary boxes for futures (same layout as TOTAL, different content)
  const summaryCards: Array<{
    key: string;
    label: string;
    value: string | number;
    subtitle?: string | number;
  }> = [
    {
      key: "bid",
      label: "Bid",
      value: `${bidPriceDisplay}`,
      subtitle: `Size ${bidSizeDisplay}`,
    },
    {
      key: "ask",
      label: "Ask",
      value: `${askPriceDisplay}`,
      subtitle: `Size ${askSizeDisplay}`,
    },
    {
      key: "prev-close",
      label: "Prev Close (24h)",
      value: formatNumOrDash(snap?.prev_close_24h),
    },
    {
      key: "local-date",
      label: "Local Date",
      value: sessionDateLabel,
    },
  ];

  const sessionStatsRows = [
    {
      key: "open",
      label: "Open",
      value: formatNumOrDash(snap?.open_price_24h),
      triangleValue: snap?.market_open,
      percent: buildPercentCell(snap?.market_open),
    },
    {
      key: "high",
      label: "24h High",
      value: formatNumOrDash(snap?.high_24h),
      triangleValue: snap?.market_high_pct_open,
      percent: buildPercentCell(snap?.market_high_pct_open),
    },
    {
      key: "low",
      label: "24h Low",
      value: formatNumOrDash(snap?.low_24h),
      triangleValue: snap?.market_low_pct_open,
      percent: buildPercentCell(snap?.market_low_pct_open),
    },
    {
      key: "range",
      label: "24h Range",
      value: formatNumOrDash(snap?.range_diff_24h),
      triangleValue: snap?.range_pct_24h,
      percent: buildPercentCell(snap?.range_pct_24h),
    },
    {
      key: "volume",
      label: "Session Volume",
      value: formatNumOrDash(snap?.volume, 0),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
    {
      key: "52w-high",
      label: "52w High",
      value: formatNumOrDash(snap?.high_52w),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
  ];

  return (
    <div className="mo-rt-card">
      <div className="mo-rt-left">
        {/* Shared header (same as TOTAL) */}
        <div className="mo-rt-header">
          <div className="mo-rt-header-chips">
            <span className="chip sym">{m.label}</span>
            <span className={chipClass("signal", signal || undefined)}>
              {signal || "—"}
            </span>
            <span className={chipClass("status", outcomeStatus || undefined)}>
              {outcomeStatus || "—"}
            </span>
            <span className="chip weight">Wgt: {snap?.weight ?? "—"}</span>
            <span className={healthClass}>
              Intraday {healthStatus === "green" ? "Live" : healthStatus === "red" ? "Stalled" : "Unknown"}
            </span>
            <span className="chip default">Last bar {lastBarLocal}</span>
            <span className="chip default">{lagLabel}</span>
            <span className="chip default">Capture {captureTime}</span>
          </div>
          <div className="mo-rt-header-select">
            <label htmlFor={selectId} className="future-select-label">
              Future
            </label>
            <select
              id={selectId}
              className="future-select"
              value={selectedSymbol}
              onChange={(e) => onSelectedSymbolChange(e.target.value)}
              aria-label="Select future contract"
            >
              {FUTURE_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* SAME layout as MarketTotalCard */}
        <div className="total-session-card">
          <div className="mo-rt-top total">
            <div className="mo-rt-last">
              <div className="val">{lastPriceDisplay}</div>
              <div className="label">Last</div>
            </div>
            <div className="mo-rt-change">
              <div className={`val ${closeDeltaClass}`}>
                {closeDeltaValue ??
                  (isZero(snap?.market_close) ? "0" : "—")}
              </div>
              <div className={`pct ${closeDeltaClass}`}>
                {closeDeltaPercent ??
                  (isZero(snap?.market_close_vs_open_pct) ? "0%" : "—")}
              </div>
              <div className="label">Close Δ</div>
            </div>
          </div>

          <div className="session-summary-grid">
            {summaryCards.map((card) => (
              <div className="session-summary-card" key={card.key}>
                <div className="summary-label">{card.label}</div>
                <div className="summary-value">{card.value}</div>
                {card.subtitle && (
                  <div className="summary-sub">{card.subtitle}</div>
                )}
              </div>
            ))}
          </div>

          <div className="mo-rt-session-stats">
            <div className="session-stats-header">
              <span>Metric</span>
              <span>Value</span>
              <span>Δ</span>
              <span>Δ%</span>
            </div>
            {sessionStatsRows.map((row) => (
              <div className="session-stats-row" key={row.key}>
                <span>{row.label}</span>
                <span>{row.value}</span>
                <span className="triangle-cell">
                  <span className={getTriangleClass(row.triangleValue)} />
                </span>
                <span
                  className={`triangle-percent ${row.percent.className}`}
                >
                  {row.percent.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* no right panel – same silhouette as TOTAL */}
    </div>
  );
};

export default MarketFutureCard;
