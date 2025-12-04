import React from "react";
import { FUTURE_OPTIONS } from "./marketSessionTypes.ts";
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
// Optional: separate CSS just for TOTAL look
// import "./MarketTotalCard.css";

type MarketTotalCardProps = {
  market: any;
  snap: any;
  status?: any;
  selectedSymbol: string;
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketTotalCard: React.FC<MarketTotalCardProps> = ({
  market: m,
  snap,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  const signal = snap?.bhs;
  const outcomeStatus = snap?.wndw;

  const captureTime = snap?.captured_at
    ? new Date(snap.captured_at).toLocaleTimeString()
    : "—";
  const selectId = `future-select-${m.key}`;

  const totalWeightedAverage =
    formatNum(snap?.weighted_average, 3) ??
    (isZero(snap?.weighted_average) ? 0 : "—");
  const totalInstrumentCount = snap?.instrument_count ?? 11;
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
  const lastPriceDisplay =
    formatNum(snap?.last_price) ??
    (isZero(snap?.last_price) ? 0 : "—");

  const totalSummaryCards: Array<{
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
      key: "basket",
      label: "Futures in Basket",
      value: totalInstrumentCount,
    },
    {
      key: "total-avg",
      label: "Total Weighted Avg",
      value: totalWeightedAverage,
    },
    {
      key: "local-date",
      label: "Local Date",
      value: sessionDateLabel,
    },
  ];

  const totalSessionStatsRows = [
    {
      key: "market-open",
      label: "Market Open",
      value: formatNumOrDash(snap?.open_price_24h),
      triangleValue: snap?.market_open,
      percent: buildPercentCell(snap?.market_open),
    },
    {
      key: "market-high",
      label: "Market High",
      value: formatNumOrDash(snap?.high_24h),
      triangleValue: snap?.market_high_pct_open,
      percent: buildPercentCell(snap?.market_high_pct_open),
    },
    {
      key: "market-low",
      label: "Market Low",
      value: formatNumOrDash(snap?.low_24h),
      triangleValue: snap?.market_low_pct_open,
      percent: buildPercentCell(snap?.market_low_pct_open),
    },
    {
      key: "market-close",
      label: "Market Close",
      value: formatNumOrDash(snap?.prev_close_24h),
      triangleValue: snap?.market_close_vs_open_pct,
      percent: buildPercentCell(snap?.market_close_vs_open_pct),
    },
    {
      key: "range",
      label: "Range",
      value: formatNumOrDash(snap?.market_range),
      triangleValue: snap?.market_range_pct,
      percent: buildPercentCell(snap?.market_range_pct),
    },
    {
      key: "session-volume",
      label: "Session Volume",
      value: formatNumOrDash(snap?.volume, 0),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
  ];

  return (
    <div className="mo-rt-card">
      <div className="mo-rt-left">
        {/* Shared header for TOTAL */}
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

        {/* TOTAL-specific layout */}
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
            {totalSummaryCards.map((card) => (
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
            {totalSessionStatsRows.map((row) => (
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

      {/* TOTAL does not render mo-rt-right by design */}
    </div>
  );
};

export default MarketTotalCard;
